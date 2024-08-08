package <APP-PACKAGE>;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Bundle;
import android.os.Environment;
import android.os.Looper;
import android.util.Log;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;

public class JacocoInstrumentation extends Instrumentation implements InstrumentActivityListener {

    public static final String TAG = "JacocoInstrumentation";

    private String coverageFilePath;
    private Intent mIntent;

    public JacocoInstrumentation() {
        Log.d(TAG, "Hello");
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        mIntent = new Intent(getTargetContext(), InstrumentActivity.class);
        mIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        start();
    }

    @Override
    public void onStart() {
        super.onStart();

        Looper.prepare();
        EndEmmaBroadcast broadcast = new EndEmmaBroadcast();
        InstrumentActivity activity = (InstrumentActivity) startActivitySync(mIntent);
        activity.setInstrumentActivityListener(this);
        broadcast.setInstrumentActivityListener(this);
        activity.registerReceiver(broadcast, new IntentFilter(".EndEmmaBroadcast"));
        Log.d(TAG, "EndEmmaBroadcast registered.");
    }

    @Override
    public void onActivityEnd() {
        this.generateCoverageReport();
        finish(Activity.RESULT_OK, new Bundle());
    }

    private void generateCoverageReport() {
        String fileName = "coverage-" + System.currentTimeMillis() + ".ec";
        File downloadsFile = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
        String filePath = downloadsFile + File.separator + fileName;
        Log.d(TAG, "Coverage file path:" + filePath);

        File file = new File(filePath);
        if (!file.exists()) {
            try {
                boolean created = file.createNewFile();
                if (created) {
                    Log.d(TAG, "Coverage file created at " + filePath);
                    this.coverageFilePath = filePath;
                }
            } catch (IOException e) {
                Log.d(TAG, "Failed to create coverage file at " + filePath + ". " + e.getMessage());
            }
        }

        Log.d(TAG, "Generating coverage report at " + this.coverageFilePath);

        OutputStream out = null;
        try {
            out = new FileOutputStream(this.coverageFilePath, true);
            Object agent = Class.forName("org.jacoco.agent.rt.RT").getMethod("getAgent").invoke(null);
            if (agent != null) {
                out.write((byte[]) agent.getClass().getMethod("getExecutionData", boolean.class).invoke(agent, false));
            }
        } catch (Exception e) {
            Log.d(TAG, e.toString(), e);
        } finally {
            if (out != null) {
                try {
                    out.close();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        }
    }
}