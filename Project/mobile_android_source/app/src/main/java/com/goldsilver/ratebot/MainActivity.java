package com.goldsilver.ratebot;

import android.app.Activity;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

public class MainActivity extends Activity {
    private static final String PREFS = "ratebot";
    private EditText urlInput;
    private WebView webView;
    private LinearLayout setup;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        showSetup();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void showSetup() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(28), dp(20), dp(20));
        root.setBackgroundColor(Color.rgb(238, 241, 245));

        setup = root;
        TextView title = new TextView(this);
        title.setText("Gold & Silver Rate Bot");
        title.setTextSize(26);
        title.setTextColor(Color.rgb(23, 32, 51));
        title.setPadding(0, 0, 0, dp(16));
        root.addView(title);

        TextView help = new TextView(this);
        help.setText("Enter the Mobile address shown on the PC dashboard. Example: http://192.168.1.10:5000");
        help.setTextSize(14);
        help.setTextColor(Color.rgb(92, 105, 126));
        help.setPadding(0, 0, 0, dp(12));
        root.addView(help);

        urlInput = new EditText(this);
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        urlInput.setText(prefs.getString("url", "http://192.168.1.10:5000"));
        urlInput.setSingleLine(true);
        root.addView(urlInput, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));

        Button connect = new Button(this);
        connect.setText("Connect to PC");
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(54));
        bp.topMargin = dp(14);
        root.addView(connect, bp);
        connect.setOnClickListener(v -> openDashboard());

        setContentView(root);
    }

    private void openDashboard() {
        String url = urlInput.getText().toString().trim();
        if (!url.startsWith("http://") && !url.startsWith("https://")) url = "http://" + url;
        getSharedPreferences(PREFS, MODE_PRIVATE).edit().putString("url", url).apply();

        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        webView.setWebViewClient(new WebViewClient());
        setContentView(webView);
        webView.loadUrl(url);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else if (webView != null) showSetup();
        else super.onBackPressed();
    }
}
