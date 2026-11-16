// Lead-only real-card scenario, using the same upstream Windows BOINC IPC owner.
#include <chrono>
static void card_scenario(SHARED_MEM* shm, APP_CLIENT_SHM& ipc,
                          PROCESS_INFORMATION& pi, const char* command) {
    const char* large_env=getenv("KNC_E2E_LARGE");
    const bool large=large_env && !strcmp(large_env,"1");
    const double screenshot_at=large?2.:30., suspend_at=large?5.:60., suspend_for=large?5.:30.;
    using Clock = std::chrono::steady_clock;
    PROCESS_INFORMATION gfx={};
    HANDLE mapping=nullptr;
    void* address=nullptr;
    auto start=Clock::now(), phase=start;
    std::ofstream times("e2e-times.tsv");
    times << "phase\twall_seconds\n";
    auto elapsed=[&](auto since){return std::chrono::duration<double>(Clock::now()-since).count();};
    auto record=[&](const char* label){times<<label<<'\t'<<elapsed(phase)<<std::endl;phase=Clock::now();};
    auto pump=[&] {
        if (!shm->heartbeat.has_msg()) shm->heartbeat.send_msg(
            "<heartbeat><working_set_size>0</working_set_size><max_working_set_size>0</max_working_set_size></heartbeat>");
        char msg[MSG_CHANNEL_SIZE];shm->app_status.get_msg(msg);
        require(!exists("e2e-abort"),"lead runner requested abort");
    };
    auto wait=[&](auto predicate,const char* reason,double timeout=180.,bool alive=true) {
        auto since=Clock::now();
        while (!predicate()) {
            pump();
            if(alive)require(WaitForSingleObject(pi.hProcess,0)==WAIT_TIMEOUT,reason);
            require(elapsed(since)<timeout,reason);Sleep(100);
        }
    };
    auto hold=[&](double seconds) {
        auto since=Clock::now();
        wait([&]{return elapsed(since)>=seconds;},"wrapper completed before timed phase",seconds+10);
    };
    auto hook=[&](const char* name) {
        std::string path=std::string("e2e-")+name;
        {std::ofstream marker(path);marker<<"ready\n";}
        wait([&]{return exists((path+".ack").c_str());},"runner verification timeout",60,false);
    };
    auto trace=[&](const char* text){return contents("knc_wrapper.log").find(text)!=std::string::npos;};
    auto control=[&](const char* message){require(shm->process_control_request.send_msg(message),"send process control");};
    auto exit=[&](bool finish) {
        wait([&]{return WaitForSingleObject(pi.hProcess,0)==WAIT_OBJECT_0;},"wrapper exit timeout",180,false);
        DWORD code=999;require(GetExitCodeProcess(pi.hProcess,&code)&&code==0,"wrapper failed");
        require(exists(BOINC_FINISH_CALLED_FILE)==finish,"finish semantics");
        require(!exists("knc_remote"),"remote lease remains");
    };
    try {
        wait([&]{mapping=attach_shmem("boinc_knc_nbody_731",&address);return mapping!=nullptr;},"live graphics mapping missing");
        auto* shared=static_cast<knc_graphics*>(address);
        auto live=[&] {
            knc_graphics copy={};
            uint32_t before=*(volatile uint32_t*)&shared->sequence;MemoryBarrier();
            memcpy(&copy,shared,sizeof(copy));MemoryBarrier();
            return !(before&1)&&before==*(volatile uint32_t*)&shared->sequence&&
                copy.magic==KNC_GRAPHICS_MAGIC&&copy.size==sizeof(copy)&&
                copy.status==KNC_RUNNING&&copy.snapshot.body_count>0;
        };
        wait(live,"no running card snapshot");record("startup");
        auto running=Clock::now();
        hold(screenshot_at);
        require(live(),"live mapping lost before screenshot");
        const char* exe=getenv("KNC_GRAPHICS_EXE");require(exe,"graphics executable missing");
        std::string graphics=std::string("\"")+exe+"\" --screenshot live-card.bmp";
        STARTUPINFOA si={};si.cb=sizeof(si);
        require(CreateProcessA(nullptr,graphics.data(),nullptr,nullptr,FALSE,0,nullptr,nullptr,&si,&gfx),"graphics launch");
        CloseHandle(gfx.hThread);
        wait([&]{return exists("live-card.bmp");},"graphics screenshot timeout",15);
        while(elapsed(running)<suspend_at)hold(std::min(1.,suspend_at-elapsed(running)));
        record("run-before-suspend");
        control("<suspend/>");
        wait([&]{return trace("signal STOP");},"card STOP missing");record("suspend-ack");
        hook("suspended");
        hold(suspend_for);record("suspended");
        control("<resume/>");
        wait([&]{return trace("signal CONT");},"card CONT missing");record("resume-ack");
        hold(2);hook("checkpoint");record("resumed-to-checkpoint");
        control("<quit/>");exit(false);
        require(!contents("knc_checkpoint").empty()&&trace("checkpoint saved"),"quit lost checkpoint");
        // Preserve the exact bytes that will be uploaded on the second launch.
        std::filesystem::copy_file("knc_checkpoint","restart-checkpoint",std::filesystem::copy_options::overwrite_existing);
        record("quit-checkpoint-transfer");hook("quit-clean");
        CloseHandle(pi.hProcess);pi.hProcess=nullptr;ipc.reset_msgs();
        std::string restart=command;
        require(CreateProcessA(nullptr,restart.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&si,&pi),"restart wrapper");
        CloseHandle(pi.hThread);
        wait([&]{return trace("checkpoint uploaded for restart")&&exists("knc_remote");},"checkpoint not uploaded");
        hook("restarted");record("restart-upload");
        wait([&]{return WaitForSingleObject(pi.hProcess,0)==WAIT_OBJECT_0;},"completion timeout",43200,false);
        exit(true);record("run-to-completion");hook("final-clean");
        require(!contents("result.data").empty(),"resolved result missing");
        require(contents("nbody_stderr.txt").find("search_likelihood")!=std::string::npos,"likelihood missing");
        require(contents("nbody_stdout.txt").find("Resumed from checkpoint")!=std::string::npos,"restore diagnostic missing");
        puts("PASS real BOINC IPC/card suspend/resume/checkpoint/restart/completion");
    } catch (...) {
        // Never intentionally kill the IPC owner before asking the wrapper to
        // abort its card task. The Python runner retains all failure evidence.
        if(pi.hProcess&&WaitForSingleObject(pi.hProcess,0)==WAIT_TIMEOUT) {
            bool sent=false;
            for(int n=0;n<1200&&WaitForSingleObject(pi.hProcess,0)==WAIT_TIMEOUT;n++) {
                if(!sent)sent=shm->process_control_request.send_msg("<abort/>");
                if(!shm->heartbeat.has_msg())shm->heartbeat.send_msg("<heartbeat/>");
                Sleep(100);
            }
        }
        if(gfx.hProcess){TerminateProcess(gfx.hProcess,1);CloseHandle(gfx.hProcess);}
        if(mapping)detach_shmem(mapping,address);
        throw;
    }
    if(gfx.hProcess){
        PostThreadMessageA(gfx.dwThreadId,WM_QUIT,0,0);
        if(WaitForSingleObject(gfx.hProcess,5000)!=WAIT_OBJECT_0)TerminateProcess(gfx.hProcess,1);
        CloseHandle(gfx.hProcess);
    }
    if(mapping)detach_shmem(mapping,address);
}
