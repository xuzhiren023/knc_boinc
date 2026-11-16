// Minimal client orchestration copied from BOINC client/app_start.cpp:133-149.
// IPC, ACL creation, mapping and message transfer are linked upstream code.
#include "boinc_win.h"
#include "app_ipc.h"
#include "shmem.h"
#include <cstddef>
#include <stdexcept>
static_assert(sizeof(MSG_CHANNEL)==1024, "Windows channel size");
static_assert(sizeof(SHARED_MEM)==8192, "Windows shared memory size");
static_assert(alignof(SHARED_MEM)==1, "Windows shared memory alignment");
static_assert(offsetof(SHARED_MEM, process_control_request)==0, "control request offset");
static_assert(offsetof(SHARED_MEM, process_control_reply)==1024, "control reply offset");
static_assert(offsetof(SHARED_MEM, graphics_request)==2048, "graphics request offset");
static_assert(offsetof(SHARED_MEM, graphics_reply)==3072, "graphics reply offset");
static_assert(offsetof(SHARED_MEM, heartbeat)==4096, "heartbeat offset");
static_assert(offsetof(SHARED_MEM, app_status)==5120, "status offset");
static_assert(offsetof(SHARED_MEM, trickle_up)==6144, "trickle up offset");
static_assert(offsetof(SHARED_MEM, trickle_down)==7168, "trickle down offset");
static void require(bool ok, const char* why) {
    if (!ok) throw std::runtime_error(why);
}
static bool exists(const char* name) { return GetFileAttributesA(name)!=INVALID_FILE_ATTRIBUTES; }
static void wait_file(const char* name, HANDLE process) {
    for (int i=0; i<100; ++i) {
        if (exists(name)) return;
        require(WaitForSingleObject(process, 0)==WAIT_TIMEOUT, "app exited prematurely");
        Sleep(100);
    }
    throw std::runtime_error(name);
}
#include "knc_client_scenarios.h"
int main(int argc, char** argv) {
    PROCESS_INFORMATION pi = {};
    HANDLE mapping = NULL;
    SHARED_MEM* shm = nullptr;
    try {
        require(argc==3 || argc==4, "usage: fake-client APP.exe local|global [wrapper-scenario]");
        bool global = !strcmp(argv[2], "global");
        char name[256];
        int i;
        for (i=0; i<1024; ++i) {
            snprintf(name, sizeof(name), "%sboinc_%d", SHM_PREFIX, i);
            mapping = create_shmem(name, sizeof(SHARED_MEM), (void**)&shm, global);
            if (mapping) break;
        }
        require(mapping && shm, "create_shmem");
        char global_name[300];
        snprintf(global_name, sizeof(global_name), "Global%c%s", char(92), name);
        HANDLE global_probe=OpenFileMappingA(FILE_MAP_ALL_ACCESS, FALSE, global_name);
        bool used_global=global_probe!=NULL;
        if (global_probe) CloseHandle(global_probe);
        require(global || !used_global, "local allocation unexpectedly global");
        APP_CLIENT_SHM ipc;
        ipc.shm = shm;
        ipc.reset_msgs();
        APP_INIT_DATA aid;
        snprintf(aid.shmem_seg_name, sizeof(aid.shmem_seg_name), "boinc_%d", i);
        aid.major_version=8; aid.minor_version=2; aid.release=8;
        aid.client_pid=GetCurrentProcessId(); aid.slot=731;
        aid.checkpoint_period=1; aid.fraction_done_start=0; aid.fraction_done_end=1;
        FILE* f=fopen(INIT_DATA_FILE, "w");
        require(f, "init_data.xml");
        require(write_init_data_file(f, aid)==0, "write_init_data_file"); fclose(f);
        STARTUPINFOA si = {}; si.cb=sizeof(si);
        char command[4096];
        if (argc==4) {
            const char* fake=getenv("KNC_FAKE_CARD"); require(fake,"KNC_FAKE_CARD missing");
            const char* task=getenv("KNC_TASK_ARGS");
            snprintf(command,sizeof(command),"\"%s\" --fake-card \"%s\" %s",argv[1],fake,task?task:"");
        } else snprintf(command,sizeof(command),"\"%s\"",argv[1]);
        require(CreateProcessA(NULL, command, NULL, NULL, FALSE, CREATE_NO_WINDOW,
            NULL, NULL, &si, &pi), "CreateProcess");
        CloseHandle(pi.hThread);
        if (argc==4) {
            wrapper_scenario(argv[3],shm,ipc,pi,command);
            CloseHandle(pi.hProcess); pi.hProcess=NULL;
            detach_shmem(mapping,shm); return 0;
        }
        double fraction=0, checkpoint=0;
        char msg[MSG_CHANNEL_SIZE];
        for (int n=0; n<150 && (fraction<=0 || checkpoint<=0); ++n) {
            if (shm->app_status.get_msg(msg)) {
                const char* p=strstr(msg, "<fraction_done>");
                if (p) fraction=atof(p+15);
                p=strstr(msg, "<checkpoint_cpu_time>");
                if (p) checkpoint=atof(p+21);
            }
            require(WaitForSingleObject(pi.hProcess, 0)==WAIT_TIMEOUT, "app exited before status");
            Sleep(100);
        }
        require(fraction>0 && fraction<1, "fraction_done missing/invalid");
        require(checkpoint>0, "checkpoint_cpu_time missing");
        void* graphics=nullptr;
        HANDLE gfx=attach_shmem("boinc_s201_731", &graphics);
        require(gfx && graphics && *static_cast<int*>(graphics)==123456, "graphics mapping");
        volatile int* work=static_cast<int*>(graphics);
        require(shm->process_control_request.send_msg("<suspend/>"), "send suspend");
        wait_file("suspend_seen", pi.hProcess);
        int paused_ticks=work[1];
        // BOINC deliberately suppresses app_status while suspended
        // (api/boinc_api.cpp:1463-1470). Drain any earlier message first.
        shm->app_status.get_msg(msg);
        for (int n=0; n<35; ++n) {
            Sleep(100);
            require(work[1]==paused_ticks, "work advanced while suspended");
            require(WaitForSingleObject(pi.hProcess, 0)==WAIT_TIMEOUT, "app exited while suspended");
        }
        require(!shm->app_status.has_msg(), "status unexpectedly published while suspended");
        require(shm->process_control_request.send_msg("<resume/>"), "send resume");
        wait_file("resume_seen", pi.hProcess);
        bool advanced=false;
        for (int n=0; n<50 && !advanced; ++n) {
            if (shm->app_status.get_msg(msg)) {
                const char* p=strstr(msg, "<fraction_done>");
                if (p) advanced=atof(p+15)>fraction;
            }
            Sleep(100);
        }
        require(advanced && work[1]>paused_ticks, "work did not resume");
        detach_shmem(gfx, graphics);
        require(shm->process_control_request.send_msg("<quit/>"), "send quit");
        require(WaitForSingleObject(pi.hProcess, 10000)==WAIT_OBJECT_0, "quit timeout");
        DWORD code; require(GetExitCodeProcess(pi.hProcess, &code) && code==0, "app failed");
        require(exists("quit_seen") && !exists(BOINC_FINISH_CALLED_FILE), "quit semantics");
        CloseHandle(pi.hProcess); pi.hProcess=NULL;
        detach_shmem(mapping, shm);
        printf("PASS %s (namespace=%s): layout=8192 progress=%g checkpoint=%g suspend/resume/quit graphics\n", argv[2], used_global ? "global" : "session", fraction, checkpoint);
        return 0;
    } catch (const std::exception& e) {
        fprintf(stderr, "FAIL: %s (Win32 error %lu)\n", e.what(), GetLastError());
        if (pi.hProcess) { TerminateProcess(pi.hProcess, 99); WaitForSingleObject(pi.hProcess, 5000); CloseHandle(pi.hProcess); }
        if (mapping) detach_shmem(mapping, shm);
        return 1;
    }
}
