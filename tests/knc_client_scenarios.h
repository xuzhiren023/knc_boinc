// Included by the S2-01 fake client; uses its upstream IPC and Win32 process.
#include "../src/knc_graphics_format.h"
#include <fstream>
#include <sstream>
#include <string>
#include <filesystem>
#include <chrono>
static std::string contents(const std::string& file) {
    std::ifstream f(file); return {std::istreambuf_iterator<char>(f),{}};
}
static void wrapper_scenario(const char* scenario, SHARED_MEM* shm, APP_CLIENT_SHM& ipc, PROCESS_INFORMATION& pi, const char* command) {
    std::string mode=scenario;
    auto heartbeat=[&] {
        if (!shm->heartbeat.has_msg()) shm->heartbeat.send_msg(
            "<heartbeat><working_set_size>0</working_set_size><max_working_set_size>0</max_working_set_size></heartbeat>");
    };
    auto wait=[&](auto predicate,const char* reason,int seconds=180) {
        for (int i=0;i<seconds*10;++i) {
            heartbeat(); if (predicate()) return;
            require(WaitForSingleObject(pi.hProcess,0)==WAIT_TIMEOUT,reason); Sleep(100);
        }
        throw std::runtime_error(reason);
    };
    auto stopped=[&] {return WaitForSingleObject(pi.hProcess,0)==WAIT_OBJECT_0;};
    auto exited=[&](DWORD expected,bool finish) {
        wait(stopped,"wrapper exit timeout");
        DWORD code=999; require(GetExitCodeProcess(pi.hProcess,&code) && code==expected,"wrapper exit code");
        require(exists(BOINC_FINISH_CALLED_FILE)==finish,"finish marker semantics");
    };
    auto trace=[&](const char* text) {return contents("knc_wrapper.log").find(text)!=std::string::npos;};
    auto cleaned=[&] {
        require(!exists("knc_remote"),"remote lease remains");
        for (auto& entry:std::filesystem::directory_iterator(getenv("KNC_FAKE_CARD")))
            require(entry.path().filename().string().rfind("task-",0)!=0,"remote task directory remains");
    };
    auto completed=[&] {
        exited(0,true); cleaned();
        require(!contents("result.data").empty(),"resolved histogram output missing");
        require(contents("nbody_stderr.txt").find("search_likelihood")!=std::string::npos,"N-body likelihood missing");
    };
    if (mode=="unreachable") {
        // BOINC temporary_exit writes this file and deliberately omits finish.
        exited(0,false);
        require(exists("boinc_temporary_exit"),"temporary exit marker missing");
        require(trace("exhausted retry_limit=2"),"bounded retry diagnostic missing");
        puts("PASS wrapper unreachable"); return;
    }
    if (mode=="real") {
        // Real tasks return only BOINC stderr, with no result.data declaration.
        bool done=false;
        auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(7200);
        while (std::chrono::steady_clock::now()<deadline) {
            heartbeat();
            if (stopped()) {done=true;break;}
            Sleep(100);
        }
        if (!done) {
            std::string remote=contents("knc_remote");
            while (!remote.empty() && (remote.back()=='\n' || remote.back()=='\r')) remote.pop_back();
            for (const char* name:{"stderr.txt","stdout.txt","progress"}) {
                std::ofstream saved(std::string("timeout-")+name,std::ios::binary);
                saved<<contents(remote+"/"+name);
            }
            require(shm->process_control_request.send_msg("<abort/>"),"send bounded real-run abort");
            wait(stopped,"real-run abort timeout",30);
            throw std::runtime_error("real 117676 exceeded two hours; fake-card app aborted");
        }
        exited(0,true); cleaned();
        require(contents("nbody_stderr.txt").find("search_likelihood")!=std::string::npos,"real N-body likelihood missing");
        puts("PASS wrapper real 117676 completed; no declared output files"); return;
    }
    double fraction=0;
    wait([&] {
        char msg[MSG_CHANNEL_SIZE];
        if (shm->app_status.get_msg(msg)) {
            auto p=strstr(msg,"<fraction_done>"); if (p) fraction=atof(p+15);
        }
        return fraction>0 && fraction<.8;
    },"wrapper did not report running progress");
    if (mode=="graphics") {
        void* address=nullptr; HANDLE mapping=nullptr;
        wait([&]{mapping=attach_shmem("boinc_knc_nbody_731",&address);return mapping!=nullptr;},"graphics mapping missing",15);
        auto* shared=static_cast<knc_graphics*>(address);
        knc_graphics copy={};
        auto sample=[&]{
            uint32_t before=*(volatile uint32_t*)&shared->sequence; MemoryBarrier();
            memcpy(&copy,shared,sizeof(copy)); MemoryBarrier();
            return !(before&1) && before==*(volatile uint32_t*)&shared->sequence &&
                copy.magic==KNC_GRAPHICS_MAGIC && copy.size==sizeof(copy);
        };
        wait([&]{return sample() && copy.snapshot.body_count>0 && copy.status==KNC_RUNNING;},"no live snapshot",15);
        uint32_t first=copy.sequence;
        // Launch the real graphics consumer in the same BOINC slot.
        PROCESS_INFORMATION gfx={}; STARTUPINFOA si={};si.cb=sizeof(si);
        std::string cmd=std::string("\"")+getenv("KNC_GRAPHICS_EXE")+"\"";
        require(CreateProcessA(nullptr,cmd.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&si,&gfx),"live graphics launch");
        require(shm->process_control_request.send_msg("<suspend/>"),"send suspend");
        wait([&]{return sample() && copy.status==KNC_SUSPENDED;},"graphics did not suspend",15);
        uint32_t paused=copy.sequence;
        wait([&]{return sample() && copy.sequence!=paused;},"suspended heartbeat stalled",5);
        std::string dir=contents("knc_remote");while(!dir.empty() && (dir.back()==10||dir.back()==13))dir.pop_back();
        wait([&]{auto file=contents(dir+"/snapshot");return sample() && file.size()==sizeof(knc_snapshot) &&
            !memcmp(file.data(),&copy.snapshot,sizeof(knc_snapshot));},"snapshot differs from x86 file",10);
        // The real reader must show suspension and then live running state.
        HWND gw=nullptr;
        for(int n=0;n<100 && !gw;n++){gw=FindWindowA("KNCNBodyGraphics","MilkyWay@home - suspended");Sleep(100);}
        require(gw,"live graphics suspended title");
        uint64_t step=copy.snapshot.step;
        require(shm->process_control_request.send_msg("<resume/>"),"send resume");
        wait([&]{return sample() && copy.status==KNC_RUNNING && copy.sequence!=first && copy.snapshot.step>step;},"snapshot did not resume",15);
        wait([&]{return FindWindowA("KNCNBodyGraphics","MilkyWay@home - running")!=nullptr;},"live graphics running title",5);
        completed();
        require(sample() && copy.status==KNC_FINISHED,"graphics did not finish");
        PostMessageA(gw,WM_CLOSE,0,0);require(WaitForSingleObject(gfx.hProcess,5000)==WAIT_OBJECT_0,"graphics exit");
        CloseHandle(gfx.hThread);CloseHandle(gfx.hProcess);detach_shmem(mapping,address);
        puts("PASS graphics relay: x86 bytes, sequence, suspended heartbeat, resume, finished, live window");return;
    }
    if (mode=="normal") {completed(); puts("PASS wrapper normal outputs"); return;}
    if (mode=="abort") {
        require(shm->process_control_request.send_msg("<abort/>"),"send abort");
        exited(202,true); cleaned(); require(trace("signal KILL"),"abort did not kill card");
        require(!exists("result.data"),"abort produced output"); puts("PASS wrapper abort"); return;
    }
    if (mode=="suspend") {
        require(shm->process_control_request.send_msg("<suspend/>"),"send suspend");
        wait([&]{return trace("signal STOP");},"card did not suspend");
        std::string dir=contents("knc_remote"); while (!dir.empty() && (dir.back()=='\n' || dir.back()=='\r')) dir.pop_back();
        // The file is independent of BOINC's suppression of suspended status.
        auto before=contents(dir+"/progress"); require(!before.empty(),"no remote progress file");
        for (int i=0;i<25;++i) {heartbeat(); Sleep(100); require(contents(dir+"/progress")==before,"card advanced while stopped");}
        require(shm->process_control_request.send_msg("<resume/>"),"send resume");
        wait([&]{return trace("signal CONT") && contents(dir+"/progress")!=before;},"card did not resume");
        completed(); puts("PASS wrapper suspend/resume"); return;
    }
    require(mode=="quit","unknown wrapper scenario");
    require(shm->process_control_request.send_msg("<quit/>"),"send quit");
    exited(0,false); cleaned();
    require(!contents("knc_checkpoint").empty() && trace("checkpoint saved"),"quit lost checkpoint");
    CloseHandle(pi.hProcess); pi.hProcess=NULL;
    ipc.reset_msgs();
    STARTUPINFOA si={}; si.cb=sizeof(si);
    std::string restart=command;
    require(CreateProcessA(NULL,restart.data(),NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,NULL,&si,&pi),"restart wrapper");
    CloseHandle(pi.hThread);
    completed();
    require(trace("checkpoint uploaded for restart"),"restart omitted checkpoint");
    require(contents("nbody_stdout.txt").find("Resumed from checkpoint")!=std::string::npos,"N-body checkpoint restore diagnostic missing");
    puts("PASS wrapper quit/checkpoint/restart");
}
