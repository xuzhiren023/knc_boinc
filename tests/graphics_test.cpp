#include "boinc_win.h"
#include "boinc_api.h"
#include "graphics2.h"
#include "knc_graphics_format.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/cygwin.h>
static void need(bool b,const char* s) {if(!b){fprintf(stderr,"FAIL %s (%lu)\n",s,GetLastError());exit(1);}}
static HWND window;
static BOOL CALLBACK find(HWND w,LPARAM pid) {DWORD p;GetWindowThreadProcessId(w,&p);if(p==DWORD(pid)&&IsWindowVisible(w))window=w;return TRUE;}
static PROCESS_INFORMATION child;
static void stop() {if(child.hProcess){TerminateProcess(child.hProcess,1);CloseHandle(child.hProcess);CloseHandle(child.hThread);child={};}}
static void launch(const char* args) {
    char exe[1024];need(cygwin_conv_path(CCP_POSIX_TO_WIN_A,"build/graphics/knc_nbody_graphics.exe",exe,sizeof(exe))==0,"native exe path");
    std::string command=char(34)+std::string(exe)+char(34)+" "+args;
    char cmd[2048];snprintf(cmd,sizeof(cmd),"%s",command.c_str());
    STARTUPINFOA si={};si.cb=sizeof(si);window=0;
    need(CreateProcessA(nullptr,cmd,nullptr,nullptr,FALSE,0,nullptr,nullptr,&si,&child),"launch");
    for(int i=0;i<100&&!window;i++){Sleep(100);EnumWindows(find,child.dwProcessId);}need(window,"window appeared");
}
static void status(const char* expected) {
    char title[256]={};for(int i=0;i<100;i++){GetWindowTextA(window,title,sizeof(title));if(strstr(title,expected))return;Sleep(100);}
    fprintf(stderr,"got title: %s\n",title);need(false,expected);
}
static void close_window(){PostMessage(window,WM_CLOSE,0,0);need(WaitForSingleObject(child.hProcess,5000)==WAIT_OBJECT_0,"clean exit");DWORD code;GetExitCodeProcess(child.hProcess,&code);need(code==0,"exit zero");CloseHandle(child.hProcess);CloseHandle(child.hThread);child={};}
int main(){atexit(stop);
    launch("");status("waiting");SetWindowPos(window,0,0,0,640,400,SWP_NOMOVE|SWP_NOZORDER);Sleep(300);status("waiting");close_window();
    boinc_parse_init_data_file();auto* shared=(knc_graphics*)boinc_graphics_make_shmem(KNC_GRAPHICS_NAME,sizeof(knc_graphics));need(shared,"real BOINC graphics mapping");
    memset(shared,0,sizeof(*shared));shared->magic=KNC_GRAPHICS_MAGIC;shared->version=1;shared->size=sizeof(*shared);shared->status=KNC_RUNNING;
    shared->snapshot.magic=KNC_SNAPSHOT_MAGIC;shared->snapshot.version=1;shared->snapshot.size=sizeof(knc_snapshot);shared->snapshot.body_count=0;shared->sequence=2;
    launch("");status("running");Sleep(5500);status("stale");
    shared->sequence=3;MemoryBarrier();shared->status=KNC_SUSPENDED;MemoryBarrier();shared->sequence=4;status("suspended");
    shared->sequence=5;MemoryBarrier();shared->status=KNC_FINISHED;MemoryBarrier();shared->sequence=6;status("finished");close_window();
    shared->sequence=7;launch("");status("waiting");close_window();
    launch("--demo build/graphics/demo.snapshot --screenshot build/graphics/window.bmp");status("demo");ShowWindow(window,SW_RESTORE);SetWindowPos(window,HWND_TOPMOST,30,30,960,640,SWP_SHOWWINDOW);SetForegroundWindow(window);Sleep(1500);close_window();
    launch("--fullscreen --demo build/graphics/demo.snapshot");status("demo");PostMessage(window,WM_KEYDOWN,VK_ESCAPE,0);need(WaitForSingleObject(child.hProcess,5000)==WAIT_OBJECT_0,"fullscreen escape");stop();
    puts("PASS window: missing shmem, zero bodies, stale sequence, suspended, finished, odd sequence, demo, resize, fullscreen, capture");
}
