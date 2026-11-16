// BOINC slot graphics helper: Win32 window, legacy OpenGL, no science threads.
#include "boinc_win.h"
#include <GL/gl.h>
#include "boinc_api.h"
#include "graphics2.h"
#include "knc_graphics_format.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <chrono>
#include <vector>
using Clock=std::chrono::steady_clock;
static HWND window;
static bool fullscreen=false;
static POINT initial_mouse;
static HDC dc;
static GLuint font,texture;
static std::string screenshot;
static knc_snapshot snapshot;
static knc_graphics incoming;
static const knc_graphics* shared=nullptr;
static uint32_t last_sequence;
static bool seen=false,demo=false;
static auto changed=Clock::now(), started=Clock::now(), retry=Clock::now();
static const char* state="waiting";
static double camera[4]={0,0,0,1};
static bool framed=false;
static auto frame_time=Clock::now();
static bool valid(const knc_snapshot& s) {
    if(s.magic!=KNC_SNAPSHOT_MAGIC || s.version!=1 || s.size!=sizeof(s) || s.body_count>KNC_MAX_BODIES ||
       !std::isfinite(s.sim_time)||!std::isfinite(s.fraction_done)||s.fraction_done<0||s.fraction_done>1) return false;
    for(uint32_t i=0;i<s.body_count;i++) {auto b=s.bodies[i];if(b.type>1||!std::isfinite(b.x)||!std::isfinite(b.y)||!std::isfinite(b.z))return false;}
    return true;
}
static void update() {
    if(demo){state="demo";return;}
    auto now=Clock::now();
    if(!shared && now>=retry){shared=(const knc_graphics*)boinc_graphics_get_shmem(KNC_GRAPHICS_NAME);retry=now+std::chrono::seconds(1);}
    state="waiting";
    if(!shared)return;
    // Windows aligned 32-bit load + full fences; producer follows header contract.
    auto seq=(const volatile uint32_t*)&shared->sequence;
    uint32_t before=*seq;MemoryBarrier();
    if(before&1)return;
    memcpy(&incoming,shared,sizeof(incoming));MemoryBarrier();
    if(before!=*seq || incoming.sequence!=before)return;
    if(incoming.magic!=KNC_GRAPHICS_MAGIC||incoming.version!=1||incoming.size!=sizeof(incoming)||incoming.status>KNC_WAITING||!valid(incoming.snapshot))return;
    if(!seen||before!=last_sequence){snapshot=incoming.snapshot;last_sequence=before;changed=now;seen=true;}
    if(now-changed>std::chrono::seconds(5)){state="stale - waiting";return;}
    static const char* names[]={"running","suspended","finished","waiting"};state=names[incoming.status];
}
static void text(float x,float y,const std::string& s){glRasterPos2f(x,y);glListBase(font);glCallLists(s.size(),GL_UNSIGNED_BYTE,s.data());}
static bool capture_window(int width,int height) {
    int stride=(width*3+3)&~3;std::vector<unsigned char> pixels(size_t(stride)*height);
    glReadBuffer(GL_BACK);glReadPixels(0,0,width,height,GL_RGB,GL_UNSIGNED_BYTE,pixels.data());
    if(glGetError()!=GL_NO_ERROR)return false;
    for(int y=0;y<height;y++)for(int x=0;x<width;x++)std::swap(pixels[y*stride+x*3],pixels[y*stride+x*3+2]);
    BITMAPINFOHEADER info={};info.biSize=40;info.biWidth=width;info.biHeight=height;info.biPlanes=1;info.biBitCount=24;info.biCompression=BI_RGB;
    BITMAPFILEHEADER header={};header.bfType=0x4d42;header.bfOffBits=sizeof(header)+sizeof(info);header.bfSize=header.bfOffBits+pixels.size();
    std::ofstream file(screenshot,std::ios::binary);file.write((char*)&header,sizeof(header));file.write((char*)&info,sizeof(info));file.write((char*)pixels.data(),pixels.size());return bool(file);
}
static void render() {
    update();std::string title=std::string("MilkyWay@home - ")+state;SetWindowTextA(window,title.c_str());
    RECT r;GetClientRect(window,&r);int w=std::max(1,int(r.right)),h=std::max(1,int(r.bottom));
    glViewport(0,0,w,h);glClearColor(.015,.025,.06,1);glClear(GL_COLOR_BUFFER_BIT);
    glMatrixMode(GL_PROJECTION);glLoadIdentity();double aspect=double(w)/h;
    glOrtho(-aspect*1.3,aspect*1.3,-1.3,1.3,.1,1000);
    glMatrixMode(GL_MODELVIEW);glLoadIdentity();glTranslatef(0,0,-30);
    double seconds=std::chrono::duration<double>(Clock::now()-started).count();glRotatef(15,1,0,0);glRotatef(25+seconds*.6,0,1,0);
    bool active=demo||!strcmp(state,"running")||!strcmp(state,"finished")||!strcmp(state,"suspended");
    // Robust extent discards a few escaping outliers, never the visible stream.
    double cx=0,cy=0,cz=0,scale=1;
    if(active&&snapshot.body_count){
        for(uint32_t i=0;i<snapshot.body_count;i++){auto b=snapshot.bodies[i];cx+=b.x;cy+=b.y;cz+=b.z;}
        cx/=snapshot.body_count;cy/=snapshot.body_count;cz/=snapshot.body_count;
        double view[16];glGetDoublev(GL_MODELVIEW_MATRIX,view);
        std::vector<double> radii; radii.reserve(snapshot.body_count);
        for(uint32_t i=0;i<snapshot.body_count;i++){auto b=snapshot.bodies[i];double x=b.x-cx,y=b.y-cy,z=b.z-cz;
            radii.push_back(std::hypot(view[0]*x+view[4]*y+view[8]*z,view[1]*x+view[5]*y+view[9]*z));}
        size_t index=size_t((radii.size()-1)*.98);std::nth_element(radii.begin(),radii.begin()+index,radii.end());
        scale=std::max(1e-10,radii[index]);
        auto now=Clock::now();double dt=std::chrono::duration<double>(now-frame_time).count();frame_time=now;
        double alpha=framed?1-std::exp(-dt/1.5):1;
        double target[]={cx,cy,cz,scale};
        for(int i=0;i<4;i++)camera[i]+=alpha*(target[i]-camera[i]);
        framed=true;cx=camera[0];cy=camera[1];cz=camera[2];scale=camera[3];
    }
    // Fill the shorter viewport dimension with the robust body extent.
    double zoom=.9*std::min(1.0,aspect);scale/=zoom;
    glEnable(GL_BLEND);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
    if(active&&snapshot.body_count){
        glColor4f(.25,.42,.65,.18);glBegin(GL_LINES);
        // Galactic z=0 disc plane, in physical coordinates relative to the camera.
        double spacing=std::pow(10.0,std::floor(std::log10(std::max(1e-10,scale))));
        double gx=std::floor(cx/spacing)*spacing, gy=std::floor(cy/spacing)*spacing;
        for(int i=-8;i<=8;i++){
            glVertex3d((gx+i*spacing-cx)/scale,-8*spacing/scale,-cz/scale);
            glVertex3d((gx+i*spacing-cx)/scale,8*spacing/scale,-cz/scale);
            glVertex3d(-8*spacing/scale,(gy+i*spacing-cy)/scale,-cz/scale);
            glVertex3d(8*spacing/scale,(gy+i*spacing-cy)/scale,-cz/scale);
        }
        glEnd();
        glColor4f(.8,.65,.45,.45);glBegin(GL_LINES);
        double x=-cx/scale,y=-cy/scale,z=-cz/scale;
        glVertex3d(x-.07,y,z);glVertex3d(x+.07,y,z);glVertex3d(x,y-.07,z);glVertex3d(x,y+.07,z);glEnd();
    }
    double point_pixels=std::clamp(4.5*std::sqrt(double(w)*h/(960*640.0))*std::pow(1024.0/std::max(1u,snapshot.body_count),.18),2.0,8.0);
    float point_size=float(point_pixels*1.3/h);
    float brightness=float(std::clamp(std::sqrt(1024.0/std::max(1u,snapshot.body_count)),.3,1.0));
    glEnable(GL_BLEND);glBlendFunc(GL_SRC_ALPHA,GL_ONE);glEnable(GL_TEXTURE_2D);glBindTexture(GL_TEXTURE_2D,texture);
    // Textured quads are soft points on legacy GL 1.1; always face the viewer.
    float model[16];glGetFloatv(GL_MODELVIEW_MATRIX,model);
    auto point=[&](double x,double y,double z,bool light,float size){
        double vx=model[0]*x+model[4]*y+model[8]*z+model[12],vy=model[1]*x+model[5]*y+model[9]*z+model[13],vz=model[2]*x+model[6]*y+model[10]*z+model[14];
        if(light)glColor4f(1,.76,.32,.9*brightness);else glColor4f(.25,.58,1,.72*brightness);
        glPushMatrix();glLoadIdentity();glTranslated(vx,vy,vz);glBegin(GL_QUADS);
        glTexCoord2f(0,0);glVertex3f(-size,-size,0);glTexCoord2f(1,0);glVertex3f(size,-size,0);glTexCoord2f(1,1);glVertex3f(size,size,0);glTexCoord2f(0,1);glVertex3f(-size,size,0);glEnd();glPopMatrix();};
    if(active&&snapshot.body_count){for(uint32_t i=0;i<snapshot.body_count;i++){auto b=snapshot.bodies[i];point((b.x-cx)/scale,(b.y-cy)/scale,(b.z-cz)/scale,b.type==KNC_LIGHT,point_size);}}
    else for(int i=0;i<96;i++){double a=i*2.399963;double radius=.15+.75*sqrt(i/96.0);point(cos(a)*radius,sin(a)*radius*.55,sin(a*.7)*.25,i%7==0,.009);}
    glDisable(GL_TEXTURE_2D);glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA);
    glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,w,0,h,-1,1);glMatrixMode(GL_MODELVIEW);glLoadIdentity();glColor3f(.83,.88,.98);
    text(24,h-36,"MilkyWay@home | N-body simulation");text(24,h-62,"Gold: stars   Blue: dark matter   Grid: Galactic disc");
    char line[160];snprintf(line,sizeof(line),"Progress: %.1f%%   Status: %s",seen||demo?snapshot.fraction_done*100:0,state);text(24,32,line);
    if(active){snprintf(line,sizeof(line),"Bodies: %u   Step: %llu   Simulation time: %.4g",snapshot.body_count,(unsigned long long)snapshot.step,snapshot.sim_time);text(24,56,line);}
    if(!screenshot.empty()) {
        if(!capture_window(w,h)){fprintf(stderr,"Window capture failed");exit(1);}
        screenshot.clear();
    }
    SwapBuffers(dc);
}
static LRESULT CALLBACK proc(HWND w,UINT message,WPARAM wp,LPARAM lp){
    switch(message){
    case WM_CLOSE:DestroyWindow(w);return 0;
    case WM_DESTROY:PostQuitMessage(0);return 0;
    case WM_KEYDOWN:if(fullscreen||wp==VK_ESCAPE)DestroyWindow(w);return 0;
    case WM_LBUTTONDOWN:case WM_RBUTTONDOWN:if(fullscreen)DestroyWindow(w);return 0;
    case WM_MOUSEMOVE:if(fullscreen&&Clock::now()-started>std::chrono::seconds(2)){POINT p;GetCursorPos(&p);if(abs(p.x-initial_mouse.x)>4||abs(p.y-initial_mouse.y)>4)DestroyWindow(w);}return 0;
    case WM_SETCURSOR:if(fullscreen){SetCursor(nullptr);return TRUE;}break;
    case WM_ERASEBKGND:return 1;
    }return DefWindowProc(w,message,wp,lp);
}
int main(int argc,char** argv){
    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i],"--fullscreen"))fullscreen=true;
        else if(!strcmp(argv[i],"--screenshot")&&i+1<argc)screenshot=argv[++i];
        else if(!strcmp(argv[i],"--demo")&&i+1<argc){std::ifstream f(argv[++i],std::ios::binary);f.read((char*)&snapshot,sizeof(snapshot));if(!f||f.peek()!=EOF||!valid(snapshot)){fprintf(stderr,"Invalid demo snapshot\n");return 1;}demo=true;}
        else {fprintf(stderr,"Usage: knc_nbody_graphics [--fullscreen] [--demo FILE]\n");return 1;}
    }
    if(!demo)boinc_parse_init_data_file();
    auto instance=GetModuleHandle(nullptr);WNDCLASSA wc={};wc.style=CS_OWNDC;wc.lpfnWndProc=proc;wc.hInstance=instance;wc.lpszClassName="KNCNBodyGraphics";wc.hCursor=LoadCursor(nullptr,IDC_ARROW);
    if(!RegisterClassA(&wc))return 1;
    DWORD style=fullscreen?WS_POPUP:WS_OVERLAPPEDWINDOW;
    window=CreateWindowA(wc.lpszClassName,"MilkyWay@home",style,fullscreen?0:CW_USEDEFAULT,fullscreen?0:CW_USEDEFAULT,fullscreen?GetSystemMetrics(SM_CXSCREEN):960,fullscreen?GetSystemMetrics(SM_CYSCREEN):640,nullptr,nullptr,instance,nullptr);
    if(!window)return 1;dc=GetDC(window);
    PIXELFORMATDESCRIPTOR pfd={};pfd.nSize=sizeof(pfd);pfd.nVersion=1;pfd.dwFlags=PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL|PFD_DOUBLEBUFFER;pfd.iPixelType=PFD_TYPE_RGBA;pfd.cColorBits=24;pfd.iLayerType=PFD_MAIN_PLANE;
    int pf=ChoosePixelFormat(dc,&pfd);if(!pf||!SetPixelFormat(dc,pf,&pfd))return 1;
    HGLRC context=wglCreateContext(dc);if(!context||!wglMakeCurrent(dc,context))return 1;
    HFONT face=CreateFontA(-18,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,ANSI_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,"Segoe UI");auto old=SelectObject(dc,face);font=glGenLists(256);BOOL font_ok=wglUseFontBitmapsA(dc,0,256,font);SelectObject(dc,old);DeleteObject(face);if(!font_ok)return 1;
    unsigned char pixels[32*32*4];for(int y=0;y<32;y++)for(int x=0;x<32;x++){int i=(y*32+x)*4;double radius=hypot((x-15.5)/15.5,(y-15.5)/15.5);pixels[i]=pixels[i+1]=pixels[i+2]=255;pixels[i+3]=(unsigned char)(255*std::pow(std::max(0.0,1-radius),2));}
    glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,32,32,0,GL_RGBA,GL_UNSIGNED_BYTE,pixels);
    GetCursorPos(&initial_mouse);ShowWindow(window,SW_SHOW);UpdateWindow(window);
    MSG msg;bool quit=false;while(!quit){while(PeekMessage(&msg,nullptr,0,0,PM_REMOVE)){if(msg.message==WM_QUIT){quit=true;break;}TranslateMessage(&msg);DispatchMessage(&msg);}if(!quit){render();Sleep(33);}}
    glDeleteTextures(1,&texture);glDeleteLists(font,256);wglMakeCurrent(nullptr,nullptr);wglDeleteContext(context);ReleaseDC(window,dc);return 0;
}
