// Correctness/portability: host ledger lifecycle, no external runtime dependency.
#include <ctime>
#include <iomanip>
// Parse complete JSON rows; unknown nested fields are skipped, malformed rows
// fail closed. Values retain their type (quoted strings start with a quote).
class TurnJSON {
    const std::string& s; size_t p=0;
    void ws(){while(p<s.size() && isspace((unsigned char)s[p]))++p;}
    char take(){if(p==s.size())throw std::runtime_error("incomplete ledger JSON");return s[p++];}
    void expect(char c){ws();if(take()!=c)throw std::runtime_error("invalid ledger JSON");}
    std::string string(){
        expect(34);std::string r(1,34);
        while(true){
            unsigned char c=take();if(c==34)return r;
            if(c<32)throw std::runtime_error("control character in ledger JSON");
            if(c==92){
                c=take();
                if(c=='u'){
                    auto hex4=[&](){
                        unsigned code=0;
                        for(int i=0;i<4;i++){
                            char h=take();
                            int n=h>='0'&&h<='9'?h-'0':h>='a'&&h<='f'?h-'a'+10:h>='A'&&h<='F'?h-'A'+10:-1;
                            if(n<0)throw std::runtime_error("invalid JSON escape");
                            code=code*16+n;
                        }
                        return code;
                    };
                    unsigned code=hex4();
                    if(code>=0xd800 && code<=0xdbff){
                        if(take()!=92 || take()!='u')throw std::runtime_error("missing JSON low surrogate");
                        unsigned low=hex4();
                        if(low<0xdc00 || low>0xdfff)throw std::runtime_error("invalid JSON low surrogate");
                        code=0x10000+((code-0xd800)<<10)+(low-0xdc00);
                    }else if(code>=0xdc00 && code<=0xdfff)throw std::runtime_error("unpaired JSON surrogate");
                    if(code<0x80)r+=char(code);
                    else if(code<0x800){r+=char(0xc0|(code>>6));r+=char(0x80|(code&63));}
                    else if(code<0x10000){r+=char(0xe0|(code>>12));r+=char(0x80|((code>>6)&63));r+=char(0x80|(code&63));}
                    else {r+=char(0xf0|(code>>18));r+=char(0x80|((code>>12)&63));r+=char(0x80|((code>>6)&63));r+=char(0x80|(code&63));}
                    continue;
                }
                switch(c){
                case 34:case 92:case '/':break;
                case 'b':c=8;break;case 'f':c=12;break;
                case 'n':c=10;break;case 'r':c=13;break;case 't':c=9;break;
                default:throw std::runtime_error("invalid JSON escape");
                }
            }
            r+=char(c);
        }
    }
    std::string value(int depth){
        if(depth>64)throw std::runtime_error("ledger JSON nesting");ws();if(p==s.size())throw std::runtime_error("missing JSON value");
        if(s[p]=='"')return string();
        if(s[p]=='{' || s[p]=='['){char open=take(),end=open=='{'?'}':']';ws();if(p<s.size()&&s[p]==end){++p;return "compound";}
            do {if(open=='{'){string();expect(':');}value(depth+1);ws();char c=take();if(c==end)break;if(c!=',')throw std::runtime_error("invalid JSON compound");}while(true);return "compound";}
        size_t start=p;while(p<s.size() && s[p]!=','&&s[p]!=']'&&s[p]!='}'&&!isspace((unsigned char)s[p]))++p;
        auto v=s.substr(start,p-start);if(v.empty())throw std::runtime_error("missing JSON value");if(v=="true"||v=="false"||v=="null")return v;
        // Only JSON numbers, never NaN/Infinity or arbitrary trailing text.
        size_t n=0;if(n<v.size()&&v[n]=='-')++n;
        if(n<v.size()&&v[n]=='0')++n;else {size_t first=n;while(n<v.size()&&isdigit((unsigned char)v[n]))++n;if(first==n)throw std::runtime_error("invalid JSON number");}
        if(n<v.size()&&v[n]=='.'){size_t first=++n;while(n<v.size()&&isdigit((unsigned char)v[n]))++n;if(first==n)throw std::runtime_error("invalid JSON fraction");}
        if(n<v.size()&&(v[n]=='e'||v[n]=='E')){++n;if(n<v.size()&&(v[n]=='+'||v[n]=='-'))++n;size_t first=n;while(n<v.size()&&isdigit((unsigned char)v[n]))++n;if(first==n)throw std::runtime_error("invalid JSON exponent");}
        if(n!=v.size())throw std::runtime_error("invalid JSON value");return v;
    }
public:
    TurnJSON(const std::string& input):s(input){}
    std::map<std::string,std::string> row(){
        std::map<std::string,std::string> r;expect('{');ws();if(p<s.size()&&s[p]=='}')++p;
        else while(true){auto k=string().substr(1);expect(':');auto v=value(0);if(!r.emplace(k,v).second)throw std::runtime_error("duplicate ledger key");ws();char c=take();if(c=='}')break;if(c!=',')throw std::runtime_error("invalid ledger row");}
        ws();if(p!=s.size())throw std::runtime_error("trailing ledger data");return r;
    }
};
static double turn_time(const std::string& value){
    if(value.empty()||value[0]!='"')return -1;
    std::istringstream in(value.substr(1));std::tm t={};in>>std::get_time(&t,"%Y-%m-%dT%H:%M:%S");if(!in)return -1;
    double fraction=0;if(in.peek()=='.'){in.get();double scale=.1;while(isdigit(in.peek())){fraction+=(in.get()-'0')*scale;scale*=.1;}}
    int offset=0;char c=in.get();if(c=='+'||c=='-'){int h,m;char colon;in>>std::setw(2)>>h>>colon>>std::setw(2)>>m;if(!in||colon!=':'||h>23||m>59)return -1;offset=(h*60+m)*60*(c=='+'?1:-1);}else if(c!='Z')return -1;
    if(in.peek()!=EOF)return -1;return timegm(&t)+fraction-offset;
}
static double turn_now(){return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();}
static std::string turn_stamp(double now){
    time_t sec=time_t(now);std::tm t=*gmtime(&sec);char b[32];strftime(b,sizeof(b),"%Y-%m-%dT%H:%M:%S",&t);
    char fraction[24];snprintf(fraction,sizeof(fraction),".%06d+00:00",int((now-sec)*1e6));return std::string(b)+fraction;
}
class Turn {
    const Config c;
    std::string id;
    double queued=0;
    std::string row(const std::string& event,double now,const std::string& outcome="") const {
        return "{\"agent\":\"claude\",\"project\":\"knc-boinc\",\"cores\":[],\"timingValid\":true,\"purpose\":\"BOINC task\",\"jobId\":\""+id+
            "\",\"event\":\""+event+"\",\""+(event=="queued"?"queuedTime":"endTime")+"\":\""+turn_stamp(now)+"\""+
            (outcome.empty()?"":",\"outcome\":\""+outcome+"\"")+"}\n";
    }
    void append(const std::string& data){
        // Existing ledger only; publish requeue's two rows in one append syscall.
        int fd=open(c.ledger.c_str(),O_WRONLY|O_APPEND);if(fd<0)throw Unreachable("cannot append booking ledger");
        ssize_t n=::write(fd,data.data(),data.size());int rc=close(fd);
        if(n!=ssize_t(data.size())||rc)throw Unreachable("booking ledger append failed");
    }
    using Rows=std::map<std::string,std::map<std::string,std::string>>;
    Rows active(){
        std::ifstream f(c.ledger);if(!f)throw Unreachable("cannot read booking ledger");
        Rows rows;std::string line;
        while(std::getline(f,line)){
            if(trim(line).empty())continue;auto r=TurnJSON(line).row();
            auto key=r.count("jobId")?r["jobId"]:r["job_id"];
            if(key.empty()||key[0]!='"')throw std::runtime_error("ledger row missing jobId");
            if(r["event"]=="\"start"||r["event"]=="\"queued")rows[key.substr(1)]=r;
            else if(r["event"]=="\"finish"||r["event"]=="\"end"||r["event"]=="\"superseded")rows.erase(key.substr(1));
        }
        if(!f.eof())throw Unreachable("booking ledger read failed");return rows;
    }
public:
    bool retain=false;
    explicit Turn(const Config& config):c(config){if(c.booking)id=trim(read("knc_turn"));}
    ~Turn(){if(!retain)try{finish("wrapper-exit");}catch(const std::exception& e){log(e.what());}}
    void finish(const std::string& outcome){
        if(id.empty())return;append(row("finish",turn_now(),outcome));id.clear();queued=0;fs::remove("knc_turn");log("turn closed: "+outcome);
    }
    bool renewal_due() const {return c.booking && !id.empty() && turn_now()-queued>=9000;}
    bool ready(){
        // The DMA latch remains mandatory even when booking is disabled.
        if(!c.booking)return !fs::exists(c.latch);
        auto rows=active();double now=turn_now();
        if(!id.empty()){
            auto it=rows.find(id);
            if(it==rows.end()){id.clear();queued=0;fs::remove("knc_turn");}
            else {
                auto& r=it->second;
                if(r["project"]!="\"knc-boinc"||r["event"]!="\"queued"||r["timingValid"]!="true"||id.rfind("claude-turn-knc-boinc-",0)!=0)
                    throw std::runtime_error("saved turn is not an open knc-boinc queue");
                queued=turn_time(r["queuedTime"]);
            }
        }
        if(id.empty()||now-queued>=9000||queued>now||queued<0){
            std::string data;if(!id.empty())data=row("superseded",now,"requeued");
            auto stamp=turn_stamp(now);stamp.erase(std::remove_if(stamp.begin(),stamp.end(),[](char c){return c=='-'||c==':'||c=='.';}),stamp.end());
            stamp=stamp.substr(0,stamp.find('+'))+"Z";
            id="claude-turn-knc-boinc-"+stamp;queued=now;
            data+=row("queued",now);append(data);write("knc_turn",id+"\n");log("turn queued: "+id);
            rows=active();
        }
        if(fs::exists(c.latch))return false;
        for(auto& entry:rows){auto& r=entry.second;if(entry.first==id||r["project"]=="\"knc-boinc")continue;
            if(r["event"]=="\"start")return false; // Running foreign jobs always drain.
            double when=turn_time(r["queuedTime"]),age=now-when;
            if(r["timingValid"]=="true"&&when>=0&&age>=0&&age<10800&&when<=queued)return false;
        }
        return true;
    }
};
