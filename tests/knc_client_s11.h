#include <cmath>
// One deterministic IPC acceptance flow per S11 wrapper feature.
template<class Heartbeat,class Wait,class Stopped,class Exited,class Trace,class Cleaned>
static bool s11_scenario(const std::string& mode, SHARED_MEM* shm, PROCESS_INFORMATION& pi,
    Heartbeat heartbeat,Wait wait,Stopped stopped,Exited exited,Trace trace,Cleaned cleaned) {
    if(mode!="setup-progress" && mode!="checkpoint-config" && mode.rfind("booking",0)!=0)return false;
    auto append=[](const std::string& s){std::ofstream("jobs.jsonl",std::ios::app)<<s<<'\n';};
    auto launched=[&]{
        for(const auto& entry:std::filesystem::directory_iterator(getenv("KNC_FAKE_CARD")))
            if(entry.path().filename().string().rfind("task-",0)==0 &&
               std::filesystem::exists(entry.path()/"started"))return true;
        return false;
    };
    auto stepping=[&]{
        for(const auto& entry:std::filesystem::directory_iterator(getenv("KNC_FAKE_CARD")))
            if(entry.path().filename().string().rfind("task-",0)==0 &&
               std::filesystem::exists(entry.path()/"progress"))return true;
        return false;
    };
    auto no_start=[&]{require(!launched(),"card started before admission");};
    if(mode=="booking-disabled"){
        for(int i=0;i<15;i++){heartbeat();Sleep(100);no_start();}
        std::filesystem::remove(std::filesystem::path(getenv("KNC_FAKE_CARD"))/".dma-stop");
    }
    if(mode=="booking" || mode=="booking-requeue" || mode=="booking-quit") {
        wait([&]{return trace("turn queued");},"turn was not queued",10);
        for(int i=0;i<15;i++){heartbeat();Sleep(100);no_start();}
        if(mode=="booking-quit") {
            require(shm->process_control_request.send_msg("<quit/>"),"queued quit");
            exited(0,false);no_start();require(!exists("knc_turn"),"queued quit retained turn");
            puts("PASS wrapper booking-quit: no card launch, closed turn, no finish marker");return true;
        }
        if(mode=="booking") {
            append(R"({"jobId":"foreign-queue","event":"finish"})");
            std::filesystem::remove("dma-stop");
            for(int i=0;i<12;i++){heartbeat();Sleep(100);no_start();}
            append(std::string(R"({"jobId":"foreign-running-)")+char(0xce)+char(0xbb)+R"(","event":"finish"})");
        } else {
            require(contents("jobs.jsonl").find("superseded")!=std::string::npos,"expired turn not superseded");
            std::filesystem::remove("dma-stop");
        }
    }
    wait(launched,"card did not start",15);
    if(mode=="setup-progress") {
        void* address=nullptr;HANDLE mapping=nullptr;
        wait([&]{mapping=attach_shmem("boinc_knc_nbody_731",&address);return mapping!=nullptr;},"generation mapping missing",5);
        auto* shared=static_cast<knc_graphics*>(address);
        bool fraction=false, generation=false;
        PROCESS_INFORMATION gfx={};STARTUPINFOA si={};si.cb=sizeof(si);
        std::string cmd=std::string("\"")+getenv("KNC_GRAPHICS_EXE")+"\"";
        require(CreateProcessA(nullptr,cmd.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&si,&gfx),"setup graphics launch");
        wait([&]{
            char msg[MSG_CHANNEL_SIZE];if(shm->app_status.get_msg(msg)){auto p=strstr(msg,"<fraction_done>");if(p){double f=atof(p+15);fraction |= !stepping() &&
                (std::fabs(f-.1875)<1e-6 || std::fabs(f-.375)<1e-6 || std::fabs(f-.5625)<1e-6 || std::fabs(f-.75)<1e-6);}}
            struct Search {DWORD pid;HWND window;};Search search={gfx.dwProcessId,nullptr};
            EnumWindows([](HWND w,LPARAM p)->BOOL {auto* s=reinterpret_cast<Search*>(p);DWORD pid=0;
                GetWindowThreadProcessId(w,&pid);char cls[64]={};GetClassNameA(w,cls,sizeof(cls));
                if(pid==s->pid && !strcmp(cls,"BOINC_app"))s->window=w;return TRUE;
            },reinterpret_cast<LPARAM>(&search));
            char title[256]={};if(search.window)GetWindowTextA(search.window,title,sizeof(title));
            generation |= strstr(title,"Generating stars ") && strstr(title," / 1000");
            return fraction && generation;
        },"generation BOINC fraction/graphics text missing",20);
        wait([&]{char msg[MSG_CHANNEL_SIZE];if(shm->app_status.get_msg(msg)){auto p=strstr(msg,"<fraction_done>");return p && atof(p+15)>.75 && atof(p+15)<1;}return false;},"step weighting missing",30);
        exited(0,true);cleaned();
        require(WaitForSingleObject(gfx.hProcess,5000)==WAIT_OBJECT_0,"setup graphics exit");CloseHandle(gfx.hThread);CloseHandle(gfx.hProcess);detach_shmem(mapping,address);
        puts("PASS wrapper setup-progress: generation BOINC fraction, graphics text, weighted steps");return true;
    }
    if(mode=="booking") {
        // Long suspension releases the turn; resume must wait behind a new foreign turn.
        require(shm->process_control_request.send_msg("<suspend/>"),"booking suspend");
        wait([&]{return trace("long suspension");},"long suspend did not close turn",10);
        append(R"({"jobId":"resume-foreign","event":"start","project":"gcc-knc","timingValid":true})");
        require(shm->process_control_request.send_msg("<resume/>"),"booking resume");
        Sleep(1500);heartbeat();require(!trace("signal CONT"),"resumed ahead of foreign job");
        append(R"({"jobId":"resume-foreign","event":"end"})");
        wait([&]{return trace("signal CONT");},"admitted resume missing",10);
        require(shm->process_control_request.send_msg("<abort/>"),"booking abort");
        exited(202,true);cleaned();require(!exists("knc_turn"),"abort retained turn");
        puts("PASS wrapper booking: FIFO, running drain, DMA latch, long suspend, resume admission, abort close");return true;
    }
    exited(0,true);cleaned();
    if(mode=="booking-disabled")require(!exists("jobs.jsonl")&&!exists("knc_turn"),"disabled booking touched ledger");
    if(mode=="booking-requeue")require(!exists("knc_turn"),"completed task retained turn");
    if(mode=="checkpoint-config"){
        require(contents("knc_run.sh").find("--checkpoint-interval=180")!=std::string::npos,"configured checkpoint interval missing");
        puts("PASS wrapper checkpoint-config: non-default 180 seconds");return true;
    }
    printf("PASS wrapper %s\n",mode.c_str());return true;
}
