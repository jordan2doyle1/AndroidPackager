package <APP-PACKAGE>;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Process;

public class EndEmmaBroadcast extends BroadcastReceiver {

    InstrumentActivityListener activityListener;

    public void setInstrumentActivityListener(InstrumentActivityListener listener) {
        this.activityListener = listener;
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        if (this.activityListener != null) {
            activityListener.onActivityEnd();
        }

        Process.killProcess(Process.myPid());
    }
}