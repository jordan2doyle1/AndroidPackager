package <APP-PACKAGE>;

import static android.Manifest.permission.READ_EXTERNAL_STORAGE;
import static android.Manifest.permission.WRITE_EXTERNAL_STORAGE;
import static android.content.pm.PackageManager.PERMISSION_GRANTED;

import android.os.Bundle;
import android.util.Log;

import android.support.v4.app.ActivityCompat;
import android.support.v4.content.ContextCompat;

public class InstrumentActivity extends <LAUNCH-ACTIVITY> {

    private InstrumentActivityListener listener;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        checkStoragePermissions();
    }

    private void checkStoragePermissions() {
        Log.i(JacocoInstrumentation.TAG, "Checking Storage Permissions");
        int readCode = ContextCompat.checkSelfPermission(this, READ_EXTERNAL_STORAGE);
        int writeCode = ContextCompat.checkSelfPermission(this, WRITE_EXTERNAL_STORAGE);
        Log.i(JacocoInstrumentation.TAG, "Read and write codes: " + readCode + "/" + writeCode);

        if (writeCode != PERMISSION_GRANTED || readCode != PERMISSION_GRANTED) {
            Log.i(JacocoInstrumentation.TAG, "Asking for storage permissions.");
            ActivityCompat.requestPermissions(this, new String[]{WRITE_EXTERNAL_STORAGE}, PERMISSION_GRANTED);
            ActivityCompat.requestPermissions(this, new String[]{READ_EXTERNAL_STORAGE}, PERMISSION_GRANTED);
        }
    }

    public void setInstrumentActivityListener(InstrumentActivityListener listener) {
        this.listener = listener;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        super.finish();

        if (listener != null) {
            listener.onActivityEnd();
        }
    }
}