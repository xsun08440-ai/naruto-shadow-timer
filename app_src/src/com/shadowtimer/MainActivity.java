package com.shadowtimer;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final String AS_PACKAGE = "com.aojoy.airscript";
    private static final String GAME_PACKAGE = "com.tencent.KiHan";
    private static final String RUN_URI = "com.aojoy.airscript://run?local=shadow_timer";
    private static final String STOP_URI = "ascript://stop";

    private TextView statusView;
    private final Handler handler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.parseColor("#0B1220"));
        getWindow().setNavigationBarColor(Color.parseColor("#0B1220"));
        setContentView(buildUi());
    }

    private View buildUi() {
        int pad = dp(22);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, dp(28), pad, dp(28));
        root.setBackgroundColor(Color.parseColor("#0B1220"));

        TextView title = new TextView(this);
        title.setText("替身计时器");
        title.setTextColor(Color.parseColor("#F4F8FF"));
        title.setTextSize(28);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("火影忍者手游 · 左右独立 15 秒");
        subtitle.setTextColor(Color.parseColor("#8FA6C4"));
        subtitle.setTextSize(14);
        subtitle.setPadding(0, dp(6), 0, dp(22));
        root.addView(subtitle);

        LinearLayout statusCard = new LinearLayout(this);
        statusCard.setOrientation(LinearLayout.VERTICAL);
        statusCard.setPadding(dp(16), dp(14), dp(16), dp(14));
        statusCard.setBackground(rounded(Color.parseColor("#121D30"), dp(14),
                Color.parseColor("#263B59"), dp(1)));

        TextView statusTitle = new TextView(this);
        statusTitle.setText("运行状态");
        statusTitle.setTextColor(Color.parseColor("#8FA6C4"));
        statusTitle.setTextSize(12);
        statusCard.addView(statusTitle);

        statusView = new TextView(this);
        statusView.setText("准备就绪");
        statusView.setTextColor(Color.parseColor("#74F0B1"));
        statusView.setTextSize(18);
        statusView.setTypeface(Typeface.DEFAULT_BOLD);
        statusView.setPadding(0, dp(6), 0, 0);
        statusCard.addView(statusView);
        root.addView(statusCard);

        Button primary = makeButton("启动计时器并进入游戏", true);
        LinearLayout.LayoutParams primaryLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(58));
        primaryLp.topMargin = dp(22);
        root.addView(primary, primaryLp);
        primary.setOnClickListener(v -> startTimer(true));

        Button onlyTimer = makeButton("只启动计时器", false);
        LinearLayout.LayoutParams onlyLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(52));
        onlyLp.topMargin = dp(12);
        root.addView(onlyTimer, onlyLp);
        onlyTimer.setOnClickListener(v -> startTimer(false));

        Button stop = makeButton("停止计时器", false);
        stop.setTextColor(Color.parseColor("#FF9B9B"));
        LinearLayout.LayoutParams stopLp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(48));
        stopLp.topMargin = dp(12);
        root.addView(stop, stopLp);
        stop.setOnClickListener(v -> stopTimer());

        TextView tipsTitle = new TextView(this);
        tipsTitle.setText("首次使用");
        tipsTitle.setTextColor(Color.parseColor("#F4F8FF"));
        tipsTitle.setTextSize(16);
        tipsTitle.setTypeface(Typeface.DEFAULT_BOLD);
        tipsTitle.setPadding(0, dp(28), 0, dp(10));
        root.addView(tipsTitle);

        TextView tips = new TextView(this);
        tips.setText("1. AScript 需要开启无障碍、悬浮窗和屏幕录制权限。\n"
                + "2. 每次重启手机后，重新进入本应用点一次启动即可。\n"
                + "3. 进入对局后，左上/右上会自动出现两个计时器。\n"
                + "4. 只读取屏幕顶部像素，不读取游戏进程。");
        tips.setTextColor(Color.parseColor("#A8BCD6"));
        tips.setTextSize(14);
        tips.setLineSpacing(dp(5), 1.0f);
        root.addView(tips);

        TextView footer = new TextView(this);
        footer.setText("需要已安装 AScript 4.0.12+");
        footer.setTextColor(Color.parseColor("#607896"));
        footer.setTextSize(12);
        footer.setGravity(Gravity.CENTER);
        footer.setPadding(0, dp(26), 0, 0);
        root.addView(footer);

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(Color.parseColor("#0B1220"));
        scroll.addView(root);
        return scroll;
    }

    private Button makeButton(String text, boolean primary) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(16);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setAllCaps(false);
        b.setTextColor(primary ? Color.parseColor("#241700") : Color.parseColor("#DCEAFF"));
        b.setBackground(rounded(
                primary ? Color.parseColor("#FFC23D") : Color.parseColor("#121D30"),
                dp(14),
                primary ? Color.parseColor("#FFC23D") : Color.parseColor("#2D4666"),
                dp(1)));
        return b;
    }

    private GradientDrawable rounded(int fill, int radius, int stroke, int strokeWidth) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(fill);
        d.setCornerRadius(radius);
        if (strokeWidth > 0) {
            d.setStroke(strokeWidth, stroke);
        }
        return d;
    }

    private void startTimer(boolean launchGame) {
        if (!isInstalled(AS_PACKAGE)) {
            status("未安装 AScript");
            Toast.makeText(this, "请先安装 AScript", Toast.LENGTH_LONG).show();
            return;
        }
        try {
            Intent run = new Intent(Intent.ACTION_VIEW, Uri.parse(RUN_URI));
            run.setPackage(AS_PACKAGE);
            run.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(run);
            status("计时器启动中…");
            if (launchGame) {
                handler.postDelayed(() -> {
                    launchGame();
                    handler.postDelayed(this::finish, 900);
                }, 2200);
            }
        } catch (Exception e) {
            status("启动失败：" + e.getClass().getSimpleName());
            Toast.makeText(this, "无法启动 AScript，请先手动打开一次", Toast.LENGTH_LONG).show();
        }
    }

    private void launchGame() {
        try {
            Intent game = getPackageManager().getLaunchIntentForPackage(GAME_PACKAGE);
            if (game == null) {
                status("未安装火影忍者");
                return;
            }
            game.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(game);
            status("已进入游戏");
        } catch (Exception e) {
            status("游戏启动失败");
        }
    }

    private void stopTimer() {
        try {
            Intent stop = new Intent(Intent.ACTION_VIEW, Uri.parse(STOP_URI));
            stop.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(stop);
            status("已发送停止命令");
        } catch (ActivityNotFoundException e) {
            status("AScript 未安装");
        }
    }

    private boolean isInstalled(String pkg) {
        try {
            getPackageManager().getPackageInfo(pkg, 0);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private void status(String text) {
        statusView.setText(text);
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }
}


