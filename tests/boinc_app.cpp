// Test app using the real BOINC API, in wrapper (cooperative control) mode.
#include "boinc_api.h"
#include "graphics2.h"
#include "util.h"
#include <cstdio>
int main() {
    BOINC_OPTIONS opt;
    boinc_options_defaults(opt);
    opt.direct_process_action = 0;
    opt.normal_thread_priority = 1;
    if (boinc_init_options(&opt)) return 2;
    if (boinc_is_standalone()) {
        boinc_fraction_done(0.5);
        boinc_checkpoint_completed();
        puts("PASS standalone");
        return boinc_finish(0);
    }
    // The fake client's separate process attaches using the graphics naming rule.
    volatile int* gfx = static_cast<int*>(boinc_graphics_make_shmem("s201", 2*sizeof(int)));
    if (!gfx) return 3;
    gfx[0] = 123456;
    gfx[1] = 0; // test work counter, independent of API status messages
    bool previous = false;
    double progress = .1;
    for (int n=0; n<600; ++n) {
        BOINC_STATUS status;
        boinc_get_status(&status);
        if (status.quit_request) {
            FILE* f = fopen("quit_seen", "w");
            if (!f) return 4;
            fclose(f);
            // A wrapper quits without marking the task successfully finished.
            return 0;
        }
        if (bool(status.suspended) != previous) {
            FILE* f = fopen(status.suspended ? "suspend_seen" : "resume_seen", "w");
            if (!f) return 5;
            fclose(f);
            previous = status.suspended;
        }
        if (!status.suspended) {
            ++gfx[1];
            progress += .001;
            boinc_fraction_done(progress);
            if (boinc_time_to_checkpoint()) boinc_checkpoint_completed();
        }
        boinc_sleep(.1);
    }
    return 6;
}
