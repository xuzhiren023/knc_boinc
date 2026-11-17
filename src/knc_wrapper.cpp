// Host-only BOINC wrapper. The card process owns no BOINC state.
#include "boinc_api.h"
#include "graphics2.h"
#include "knc_graphics_format.h"
#include <cstring>
#include <functional>
#include "filesys.h"
#include "util.h"
#include <sys/cygwin.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>
#include <map>
#include <vector>
#include <chrono>
#include <stdexcept>
#include <cmath>
#include <algorithm>
namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;
struct Unreachable: std::runtime_error { using std::runtime_error::runtime_error; };
static std::string trim(std::string s) {
    auto b=s.find_first_not_of(" \t\r\n"), e=s.find_last_not_of(" \t\r\n");
    return b==s.npos ? "" : s.substr(b,e-b+1);
}
static std::string quote(const std::string& s) {
    std::string r(1,39);
    for (char c:s) r += c==39 ? std::string({39,34,39,34,39}) : std::string(1,c);
    return r+char(39);
}
static fs::path posix(const std::string& s) {
    if (s.find(char(92))==s.npos && !(s.size()>1 && s[1]==':')) return s;
    ssize_t n=cygwin_conv_path(CCP_WIN_A_TO_POSIX,s.c_str(),nullptr,0);
    if (n<0) throw std::runtime_error("cannot convert path: "+s);
    std::vector<char> b(n);
    if (cygwin_conv_path(CCP_WIN_A_TO_POSIX,s.c_str(),b.data(),b.size())) throw std::runtime_error("path conversion failed");
    return b.data();
}
static std::string native(const fs::path& p) {
    auto s=fs::absolute(p).string();
    ssize_t n=cygwin_conv_path(CCP_POSIX_TO_WIN_A,s.c_str(),nullptr,0);
    if (n<0) throw std::runtime_error("native path conversion failed");
    std::vector<char> b(n);
    if (cygwin_conv_path(CCP_POSIX_TO_WIN_A,s.c_str(),b.data(),b.size())) throw std::runtime_error("native path conversion failed");
    return b.data();
}
static std::string read(const fs::path& p) { std::ifstream f(p); return {std::istreambuf_iterator<char>(f),{}}; }
static void write(const fs::path& p, const std::string& s) {
    std::ofstream f(p); f<<s; if (!f) throw std::runtime_error("write failed: "+p.string());
}
static void log(const std::string& s) {
    std::cerr<<"knc_wrapper: "<<s<<std::endl;
    std::ofstream("knc_wrapper.log",std::ios::app)<<s<<'\n';
}
struct Config {
    std::string host,user,key,known_hosts,ssh="C:/Windows/System32/OpenSSH/ssh.exe",scp="C:/Windows/System32/OpenSSH/scp.exe";
    std::string base="/tmp/knc-boinc", app="milkyway_nbody.mic";
    fs::path package;
    int threads=240,retries=3,connect=10,bodies=64;
    double poll=10,checkpoint_timeout=60,snapshot_interval=5;
    Config(const fs::path& file, const fs::path& exe) {
        package=exe/"card";
        std::ifstream f(file); if (!f) throw std::runtime_error("cannot read knc_wrapper.cfg");
        std::string line;
        while (std::getline(f,line)) {
            line=trim(line); if (line.empty() || line[0]=='#') continue;
            auto eq=line.find('='); if (eq==line.npos) throw std::runtime_error("config needs key=value");
            auto k=trim(line.substr(0,eq)), v=trim(line.substr(eq+1));
            if (k=="host") host=v; else if (k=="user") user=v; else if (k=="ssh_key") key=v;
            else if (k=="known_hosts") known_hosts=v;
            else if (k=="ssh_path") ssh=v; else if (k=="scp_path") scp=v;
            else if (k=="remote_base") base=v; else if (k=="app") app=v;
            else if (k=="package_dir") package=posix(v);
            else if (k=="OMP_NUM_THREADS") threads=std::stoi(v);
            else if (k=="retry_limit") retries=std::stoi(v);
            else if (k=="connect_timeout") connect=std::stoi(v);
            else if (k=="poll_interval") poll=std::stod(v);
            else if (k=="checkpoint_timeout") checkpoint_timeout=std::stod(v);
            else if (k=="snapshot_interval") snapshot_interval=std::stod(v);
            else if (k=="bodies") bodies=std::stoi(v);
            else throw std::runtime_error("unknown config key: "+k);
        }
        if (package.is_relative()) package=file.parent_path()/package;
        package=fs::absolute(package);
        if (threads<1 || retries<0 || retries>100 || connect<1 || connect>600 || bodies<1 ||
            !std::isfinite(snapshot_interval) || snapshot_interval<.05 || snapshot_interval>3600 ||
            !std::isfinite(poll) || poll<.05 || poll>3600 || !std::isfinite(checkpoint_timeout) || checkpoint_timeout<1)
            throw std::runtime_error("config value out of range");
        if (app.empty() || app=="." || app==".." || app.find('/')!=app.npos ||
            app.find(char(92))!=app.npos || app.find(char(13))!=app.npos || app.find(char(10))!=app.npos)
            throw std::runtime_error("app must be a basename");
        if (base.size()<2 || base[0]!='/' || base.find_first_not_of("/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-. ")!=base.npos)
            throw std::runtime_error("remote_base must be an absolute directory");
        for (const auto& part:fs::path(base)) if (part==".." || part==".") throw std::runtime_error("unsafe remote_base");
        while (base.back()=='/') base.pop_back();
    }
};
static std::function<void()> graphics_tick, graphics_wait;
// No local shell interpolation. Every child is timed, including a hung scp.
static int command(const std::vector<std::string>& args, double timeout, std::string& out) {
    std::string pattern=(fs::path(getenv("TMPDIR") ? getenv("TMPDIR") : ".")/"knc-command.XXXXXX").string();
    std::vector<char> temp(pattern.begin(),pattern.end()); temp.push_back(0);
    int fd=mkstemp(temp.data()); if (fd<0) throw std::runtime_error("mkstemp failed");
    std::vector<char*> av; for (auto& a:args) av.push_back(const_cast<char*>(a.c_str())); av.push_back(nullptr);
    pid_t child=fork();
    if (child<0) {close(fd); unlink(temp.data()); throw std::runtime_error("fork failed");}
    if (!child) {
        setpgid(0,0); dup2(fd,STDOUT_FILENO); close(fd);
        int nullfd=open("/dev/null",O_RDONLY); if (nullfd>=0) {dup2(nullfd,STDIN_FILENO); close(nullfd);}
        execvp(av[0],av.data()); _exit(127);
    }
    close(fd); setpgid(child,child);
    int status=0; auto start=Clock::now();
    while (waitpid(child,&status,WNOHANG)==0) {
        if (std::chrono::duration<double>(Clock::now()-start).count()>timeout) {
            kill(-child,SIGKILL); kill(child,SIGKILL); waitpid(child,&status,0); break;
        }
        if (graphics_tick) graphics_tick();
        boinc_sleep(.05);
    }
    out=read(temp.data()); unlink(temp.data());
    return WIFEXITED(status) ? WEXITSTATUS(status) : 124;
}
class Card {
    const Config& c;
    fs::path fake;
    std::vector<std::string> options(bool copy) const {
        std::vector<std::string> a{posix(copy?c.scp:c.ssh).string()};
        // -O: legacy protocol; -T: OpenSSH 9.x rejects quoted remote names in legacy downloads ("filename does not match request").
        if (copy) {a.push_back("-O"); a.push_back("-T");} else a.push_back("-T");
        for (auto s:{"BatchMode=yes","StrictHostKeyChecking=yes","ConnectionAttempts=1"}) {a.push_back("-o"); a.push_back(s);}
        if (!c.known_hosts.empty()) a.insert(a.end(),{"-o","UserKnownHostsFile="+c.known_hosts});
        a.insert(a.end(),{"-o","ConnectTimeout="+std::to_string(c.connect),"-i",native(posix(c.key))});
        return a;
    }
    template<class F> void retry(const std::string& operation, F action) const {
        for (int n=0;n<=c.retries;++n) {
            if ((fake.empty() || !fs::exists(fake/".unreachable")) && action()) return;
            if (graphics_wait) graphics_wait();
            log(operation+" failed (attempt "+std::to_string(n+1)+"/"+std::to_string(c.retries+1)+")");
            if (n<c.retries) boinc_sleep(std::min(c.poll,1.0));
        }
        throw Unreachable("card unreachable: "+operation+" exhausted retry_limit="+std::to_string(c.retries));
    }
public:
    std::string dir;
    Card(const Config& config,const fs::path& fake_dir):c(config),fake(fake_dir) {
        if (!fake.empty()) {fake=fs::absolute(fake); fs::create_directories(fake);}
        else {
            if (!c.known_hosts.empty() && !fs::is_regular_file(posix(c.known_hosts)))
                throw std::runtime_error("known_hosts file missing: "+c.known_hosts);
            auto safe=[](const std::string& s){return !s.empty() && s[0]!='-' && s.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")==s.npos;};
            if (!safe(c.host) || !safe(c.user) || c.key.empty()) throw std::runtime_error("host, user and ssh_key required");
        }
        std::string prefix=fake.empty() ? c.base : fake.string();
        dir=trim(read("knc_remote"));
        if (!dir.empty()) {
            std::string suffix=dir.substr(std::min(dir.size(),prefix.size()));
            if (dir.compare(0,prefix.size(),prefix) || suffix.rfind("/task-",0)!=0 || suffix.find('/',1)!=suffix.npos ||
                suffix.find_first_not_of("/task-0123456789")!=suffix.npos) throw std::runtime_error("unsafe saved remote lease");
        } else {
            dir=prefix+"/task-"+std::to_string(getpid())+"-"+std::to_string(std::chrono::system_clock::now().time_since_epoch().count());
        }
    }
    std::string exec(const std::string& script) const {
        std::string out;
        retry("remote command",[&]{
            auto a=fake.empty()?options(false):std::vector<std::string>{"/bin/bash","-c"};
            if (fake.empty()) a.insert(a.end(),{"--",c.user+"@"+c.host});
            a.push_back(script); return command(a,c.connect+5,out)==0;
        }); return out;
    }
    void copy(const fs::path& local,const std::string& remote,bool upload) const {
        retry(upload?"upload":"download",[&]{
            if (!fake.empty()) {
                std::error_code ec; fs::copy_file(upload?local:fs::path(remote),upload?fs::path(remote):local,fs::copy_options::overwrite_existing,ec);
                return !ec;
            }
            auto a=options(true); a.push_back("--");
            std::string r=c.user+"@"+c.host+":"+quote(remote);
            a.push_back(upload?native(local):r); a.push_back(upload?r:native(local));
            std::string out; return command(a,c.connect+30,out)==0;
        });
    }
    bool snapshot(const fs::path& local) const {
        if (!fake.empty()) {
            std::error_code ec;
            fs::copy_file(fs::path(dir)/"snapshot",local,fs::copy_options::overwrite_existing,ec);
            return !ec;
        }
        auto a=options(true); a.push_back("--");
        a.push_back(c.user+"@"+c.host+":"+quote(dir+"/snapshot")); a.push_back(native(local));
        std::string out; return command(a,c.connect+5,out)==0;
    }
    std::string at(const std::string& script) const {return exec("cd "+quote(dir)+" && "+script);}
    void signal(const char* sig) const {
        at("p=$(cat pid); case $p in ''|*[!0-9]*) exit 2;; esac; kill -"+std::string(sig)+" \"$p\"");
        log(std::string("signal ")+sig);
    }
    void clean() const {exec("rm -rf -- "+quote(dir)); fs::remove("knc_remote"); log("remote cleaned");}
};
struct State {double progress=0; int exit=-1; bool live=false,checkpoint=false,pid=false,snapshot=false;};
static State state(const Card& card) {
    auto text=card.at("if test -f exit; then printf 'exit '; cat exit; fi; "
        "if test -f pid; then p=$(cat pid); case $p in ''|*[!0-9]*) exit 2;; esac; echo pid 1; "
        "if kill -0 \"$p\" 2>/dev/null; then echo live 1; fi; fi; "
        "if test -f progress; then printf 'progress '; cat progress; fi; "
        "if test -f snapshot; then echo snapshot 1; fi; "
        "if test -f checkpoint.ready; then echo checkpoint 1; fi; true");
    State s; std::istringstream in(text); std::string k; double v;
    while (in>>k>>v) {
        if (!std::isfinite(v)) throw std::runtime_error("non-finite remote status");
        if (k=="exit") {if (v<0 || v>255 || v!=std::floor(v)) throw std::runtime_error("invalid exit status"); s.exit=int(v);}
        else if (k=="live") s.live=v==1; else if (k=="pid") s.pid=v==1;
        else if (k=="snapshot") s.snapshot=v==1;
        else if (k=="checkpoint") s.checkpoint=v==1;
        else if (k=="progress") s.progress=std::clamp(v,0.0,1.0);
    }
    return s;
}
static fs::path resolved(const char* logical) {
    char name[4096]; int rc=boinc_resolve_filename(logical,name,sizeof(name));
    if (rc) throw std::runtime_error(std::string("resolve failed: ")+logical);
    return fs::absolute(posix(name));
}
// File operands from the pinned nbody/src/main.c popt table. Keep strings
// such as visualizer-args opaque; they are not filenames.
struct TaskFile { fs::path local; std::string remote; bool input=false,output=false,executable=false,optional_output=false; };
struct Task {
    std::vector<std::string> args;
    std::vector<TaskFile> files;
    std::string checkpoint;
    Task(std::vector<std::string> incoming,const Config& c,const Card& card) {
        if (incoming.empty()) incoming={"-f","params.lua","-h","input.hist","-z","histogram.txt",
            "--seed","670828913","--print-histogram",std::to_string(c.bodies)};
        auto file=[&](const std::string& name,char kind) {
            if (name.empty()) throw std::runtime_error("empty task filename");
            auto local=resolved(name.c_str()).lexically_normal();
            auto it=std::find_if(files.begin(),files.end(),[&](const TaskFile& f){return f.local==local;});
            if (it==files.end()) {
                files.push_back({local,card.dir+"/files/"+std::to_string(files.size())});
                it=files.end()-1;
            }
            if (kind=='i' || kind=='v') it->input=true;
            if (kind=='o' || kind=='a') it->output=true;
            if (kind=='v') it->executable=true;
            if (kind=='c') {checkpoint=it->remote; it->optional_output=true;}
            return it->remote;
        };
        const std::map<std::string,char> rules={
            {"input-file",'i'},{"histogram-file",'i'},{"match-histogram",'i'},
            {"histoout-file",'o'},{"output-file",'o'},{"checkpoint",'c'},{"visualizer-bin",'v'}};
        const std::map<char,std::string> shorts={{'f',"input-file"},{'h',"histogram-file"},
            {'s',"match-histogram"},{'z',"histoout-file"},{'o',"output-file"},{'c',"checkpoint"},
            {'w',"checkpoint-interval"},{'n',"nthreads"},{'e',"seed"},{'d',"device"},{'p',"p"}};
        auto takes_value=[&](const std::string& key) {
            return rules.count(key) || key=="checkpoint-interval" || key=="nthreads" ||
                key=="snapshot-interval" || key=="seed" || key=="device" || key=="platform" || key=="np" || key=="visualizer-args";
        };
        bool threads=false,interval=false,options=true;
        for (size_t i=0;i<incoming.size();++i) {
            std::string arg=incoming[i];
            if (options && arg=="--") { options=false; args.push_back(arg); continue; }
            if (options && arg.size()>1 && arg[0]=='-') {
                std::string key; size_t value_at=std::string::npos;
                if (arg.rfind("--",0)==0 || arg=="-np" || arg.rfind("-np=",0)==0) {
                    size_t start=arg[1]=='-'?2:1, eq=arg.find('=');
                    key=arg.substr(start,eq==arg.npos?arg.npos:eq-start);
                    if (eq!=arg.npos) value_at=eq+1;
                } else {
                    // popt short clusters: stop at the first option taking an operand.
                    for (size_t j=1;j<arg.size();++j) {
                        auto it=shorts.find(arg[j]);
                        if (it!=shorts.end() && takes_value(it->second)) {
                            key=it->second;
                            if (j+1<arg.size()) value_at=j+1;
                            break;
                        }
                    }
                }
                threads |= key=="nthreads"; interval |= key=="checkpoint-interval";
                if (takes_value(key)) {
                    auto rule=rules.find(key);
                    if (value_at!=arg.npos) {
                        if (rule!=rules.end()) arg=arg.substr(0,value_at)+file(arg.substr(value_at),rule->second);
                        else if (key=="nthreads") arg=arg.substr(0,value_at)+std::to_string(c.threads);
                        args.push_back(arg);
                    } else {
                        args.push_back(arg);
                        if (++i==incoming.size()) throw std::runtime_error("missing operand: "+arg);
                        args.push_back(key=="nthreads"?std::to_string(c.threads):
                            rule==rules.end()?incoming[i]:file(incoming[i],rule->second));
                    }
                    continue;
                }
                args.push_back(arg); continue;
            }
            // popt's POSIXMEHARDER ends option parsing at the first positional value.
            options=false;
            auto local=resolved(arg.c_str());
            args.push_back(fs::is_regular_file(local)?file(arg,'a'):arg);
        }
        // Prepend defaults so POSIX parsing cannot mistake them for Lua parameters.
        std::vector<std::string> defaults={"--snapshot-interval",std::to_string(c.snapshot_interval)};
        if (checkpoint.empty()) {checkpoint=card.dir+"/checkpoint"; defaults.insert(defaults.end(),{"--checkpoint",checkpoint});}
        if (!interval) defaults.push_back("--checkpoint-interval=1");
        if (!threads) defaults.insert(defaults.end(),{"--nthreads",std::to_string(c.threads)});
        args.insert(args.begin(),defaults.begin(),defaults.end());
    }
    void stage(const Card& card) const {
        card.at("mkdir -p files");
        for (const auto& f:files) {
            if (f.input || fs::is_regular_file(f.local)) card.copy(f.local,f.remote,true);
            if (f.executable) card.at("chmod u+x "+quote(f.remote));
        }
    }
    void collect(const Card& card) const {
        for (const auto& f:files) {
            if (f.output || (f.optional_output && !card.at("if test -f "+quote(f.remote)+"; then echo yes; fi").empty()))
                card.copy(f.local,f.remote,false);
        }
    }
};
// Graphics failures must never turn a science task into a failed workunit.
class Graphics {
    knc_graphics* memory;
    knc_snapshot frame={};
    Clock::time_point fetched=Clock::now()-std::chrono::hours(1), beat=fetched;
public:
    uint32_t status=KNC_WAITING;
    Graphics():memory((knc_graphics*)boinc_graphics_make_shmem(KNC_GRAPHICS_NAME,sizeof(knc_graphics))) {
        frame.magic=KNC_SNAPSHOT_MAGIC; frame.version=1; frame.size=sizeof(frame);
        if (!memory) log("graphics mapping unavailable");
        publish();
    }
    void publish() {
        if (!memory) return;
        uint32_t seq=__atomic_load_n(&memory->sequence,__ATOMIC_RELAXED);
        __atomic_store_n(&memory->sequence,seq+1,__ATOMIC_SEQ_CST);
        memory->magic=KNC_GRAPHICS_MAGIC; memory->version=1; memory->size=sizeof(*memory);
        memory->status=status; memset(memory->reserved,0,sizeof(memory->reserved));memory->snapshot=frame;
        __atomic_thread_fence(__ATOMIC_SEQ_CST);
        __atomic_store_n(&memory->sequence,seq+2,__ATOMIC_SEQ_CST);beat=Clock::now();
    }
    void heartbeat() {if (Clock::now()-beat>=std::chrono::seconds(1)) publish();}
    void fetch(const Card& card,const State& s,double interval) {
        if (!s.snapshot || (s.exit<0 && std::chrono::duration<double>(Clock::now()-fetched).count()<interval)) return;
        fetched=Clock::now();
        if (!card.snapshot("knc_snapshot.tmp")) return;
        knc_snapshot next={};
        std::ifstream f("knc_snapshot.tmp",std::ios::binary);
        f.read((char*)&next,sizeof(next));
        bool ok=f && f.peek()==EOF && next.magic==KNC_SNAPSHOT_MAGIC && next.version==1 &&
            next.size==sizeof(next) && next.body_count<=KNC_MAX_BODIES && !next.reserved[0] && !next.reserved[1] &&
            std::isfinite(next.sim_time) && std::isfinite(next.fraction_done) &&
            next.fraction_done>=0 && next.fraction_done<=1;
        if(ok) for(uint32_t i=0;i<KNC_MAX_BODIES;i++) {
            auto b=next.bodies[i];
            if(i<next.body_count) ok &= b.type<=KNC_LIGHT && std::isfinite(b.x) && std::isfinite(b.y) && std::isfinite(b.z);
            else ok &= b.x==0 && b.y==0 && b.z==0 && b.type==0;
        }
        f.close();
        if(ok) {frame=next;std::error_code ec;fs::rename("knc_snapshot.tmp","knc_snapshot",ec);publish();}
        else {fs::remove("knc_snapshot.tmp");log("ignored invalid graphics snapshot");}
    }
};
int main(int argc,char** argv) {
    BOINC_OPTIONS opt; boinc_options_defaults(opt); opt.direct_process_action=0; opt.normal_thread_priority=1;
    if (boinc_init_options(&opt)) return 2;
    Graphics graphics;
    graphics_tick=[&]{graphics.heartbeat();};
    graphics_wait=[&]{graphics.status=KNC_WAITING;graphics.publish();};
    try {
        fs::path fake;
        int first=1;
        if (argc>1 && std::string(argv[1])=="--fake-card") {
            if (argc<3) throw std::runtime_error("--fake-card needs DIR");
            fake=posix(argv[2]); first=3;
        }
        std::vector<std::string> incoming(argv+first,argv+argc);
        char executable[4096];
        ssize_t length=readlink("/proc/self/exe",executable,sizeof(executable)-1);
        if (length<0 || size_t(length)>=sizeof(executable)-1)
            throw std::runtime_error("cannot locate wrapper executable");
        executable[length]=0;
        fs::path exe=fs::path(executable).parent_path();
        fs::path cfg=fs::exists("knc_wrapper.cfg")?fs::absolute("knc_wrapper.cfg"):exe/"knc_wrapper.cfg";
        Config c(cfg,exe); Card card(c,fake);
        Task task(incoming,c,card);
        bool leased=fs::exists("knc_remote");
        if (!leased) {
            card.exec("test -d "+quote(card.dir)+" || mkdir "+(fake.empty()?"-p -- ":"-- ")+quote(card.dir));
            write("knc_remote",card.dir+"\n");
        }
        State s=state(card);
        if (!s.pid && s.exit<0) {
            for (const auto& entry:fs::directory_iterator(c.package)) {
                auto name=entry.path().filename().string();
                if (entry.is_regular_file() && (name==c.app || name.find(".so")!=name.npos)) card.copy(entry.path(),card.dir+"/"+name,true);
            }
            if (!fs::is_regular_file(c.package/c.app)) throw std::runtime_error("card package missing app");
            task.stage(card);
            if (fs::exists("knc_checkpoint")) {
                card.copy("knc_checkpoint",task.checkpoint,true); log("checkpoint uploaded for restart");
            }
            std::string run="#!/bin/sh\ncd "+quote(card.dir)+" || exit 125\n";
            run+="export OMP_NUM_THREADS="+std::to_string(c.threads)+" OMP_DYNAMIC=FALSE KNC_WRAPPER_FILES=1 LD_LIBRARY_PATH="+quote(card.dir)+"\n";
            run+="./"+quote(c.app);
            for (const auto& arg:task.args) run+=" "+quote(arg);
            run+=" &\n";
            run+="p=$!\nprintf '%s\n' \"$p\" > pid.tmp\nmv pid.tmp pid\nwait \"$p\"\nr=$?\nprintf '%s\n' \"$r\" > exit.tmp\nmv exit.tmp exit\n";
            write("knc_run.sh",run); card.copy("knc_run.sh",card.dir+"/run.sh",true);
            card.at("chmod u+x "+quote(c.app)+" && if mkdir started 2>/dev/null; then nohup sh ./run.sh >stdout.txt 2>stderr.txt </dev/null & fi");
        } else {
            log("reattached remote lease");
            BOINC_STATUS initial; boinc_get_status(&initial);
            if (s.live && !initial.suspended) card.signal("CONT");
        }
        graphics.status=KNC_RUNNING; graphics.publish();
        bool suspended=false; auto last=Clock::now()-std::chrono::hours(1);
        auto missing_since=Clock::now();
        while (true) {
            graphics.heartbeat();
            BOINC_STATUS b; boinc_get_status(&b);
            if (b.abort_request) {
                s=state(card); if (s.live) card.signal("KILL"); card.clean(); log("abort acknowledged"); graphics.status=KNC_FINISHED;graphics.publish(); return boinc_finish(202);
            }
            if (b.quit_request || b.no_heartbeat) {
                s=state(card);
                if (s.exit<0 && s.live) {
                    card.at("rm -f checkpoint.ready; touch checkpoint.request");
                    if (suspended) card.signal("CONT");
                    auto deadline=Clock::now()+std::chrono::duration<double>(c.checkpoint_timeout);
                    do {s=state(card); if (s.checkpoint || s.exit>=0) break; boinc_sleep(.1);} while (Clock::now()<deadline);
                    if (!s.checkpoint && s.exit<0) throw Unreachable("checkpoint request timed out; remote lease retained");
                }
                if (s.exit>=0) {log("completion won race with quit"); break;}
                if (s.live) card.signal("STOP"); // freeze the acknowledged checkpoint during transfer
                card.copy("knc_checkpoint.tmp",task.checkpoint,false);
                fs::rename("knc_checkpoint.tmp","knc_checkpoint"); boinc_checkpoint_completed(); log("checkpoint saved");
                if (s.live) card.signal("KILL"); card.clean(); log("quit acknowledged"); graphics.status=KNC_FINISHED;graphics.publish(); return 0;
            }
            if (bool(b.suspended)!=suspended) {
                s=state(card);
                if (s.live) {card.signal(b.suspended?"STOP":"CONT"); suspended=b.suspended;graphics.status=suspended?KNC_SUSPENDED:KNC_RUNNING;graphics.publish();}
            }
            if (std::chrono::duration<double>(Clock::now()-last).count()>=c.poll) {
                s=state(card); last=Clock::now();
                graphics.status=suspended?KNC_SUSPENDED:KNC_RUNNING;graphics.publish();
                boinc_fraction_done(s.progress);
                graphics.fetch(card,s,c.snapshot_interval);
                if (s.exit>=0) break;
                if (s.live) missing_since=Clock::now();
                // The supervisor publishes exit just after the app PID vanishes.
                if (!s.live && std::chrono::duration<double>(Clock::now()-missing_since).count()>c.connect+5)
                    throw std::runtime_error("remote PID disappeared without exit status");
            }
            boinc_sleep(.05);
        }
        graphics.status=KNC_FINISHED; graphics.publish();
        card.copy(resolved("nbody_stdout.txt"),card.dir+"/stdout.txt",false);
        card.copy(resolved("nbody_stderr.txt"),card.dir+"/stderr.txt",false);
        if (!s.exit) task.collect(card);
        card.clean();
        // Real 196/mt results declare no output files. BOINC sends this
        // process's stderr to the validator, not our private diagnostic file.
        // Forward the complete stream, including all present/future science
        // tags, without parsing, rounding or inventing a result on failure.
        std::ifstream science(resolved("nbody_stderr.txt"),std::ios::binary);
        if (!science) throw std::runtime_error("cannot read downloaded science stderr");
        char buffer[8192];
        while (science.read(buffer,sizeof(buffer)) || science.gcount())
            std::cerr.write(buffer,science.gcount());
        std::cerr.flush();
        if (science.bad() || !std::cerr) throw std::runtime_error("cannot forward science stderr");
        if (s.exit) {log("card app exit "+std::to_string(s.exit)); return boinc_finish(s.exit);}
        fs::remove("knc_checkpoint"); boinc_fraction_done(1); log("finished"); return boinc_finish(0);
    } catch (const Unreachable& e) {
        graphics.status=KNC_FINISHED;graphics.publish();
        log(e.what()); boinc_temporary_exit(60,e.what()); return 0;
    } catch (const std::exception& e) {
        graphics.status=KNC_FINISHED;graphics.publish();
        log(e.what()); return boinc_finish(1);
    }
}
