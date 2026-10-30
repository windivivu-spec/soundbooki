package studio.windi.soundbooki;

import android.app.*;
import android.content.*;
import android.widget.*;
import org.json.*;
import java.util.concurrent.*;

/** Profile names and cached counters are display data, never entitlements. */
final class ProfileDialog {
    static String scope(Context c){return BookStore.hash(c.getSharedPreferences("settings",0).getString("cloudURL",""));}
    static SharedPreferences cache(Context c){return c.getSharedPreferences("profile-cloud-"+scope(c),0);}
    static void remember(Context c,JSONObject response,String base){
        String current=c.getSharedPreferences("settings",0).getString("cloudURL","");
        if(!current.equals(base)||!response.has("trialsRemaining"))return;
        int limit=response.optInt("trialLimit",10),left=response.optInt("trialsRemaining",-1);
        if(limit<0||left<0||left>limit)return;
        cache(c).edit().putInt("remaining",left).putInt("limit",limit).putLong("checkedAt",System.currentTimeMillis()).commit();
    }
    static int remaining(Context c){SharedPreferences p=cache(c);if(!p.contains("remaining"))return CloudClient.TRIAL_LIMIT;int used=Math.max(0,p.getInt("limit",10)-p.getInt("remaining",10));return Math.max(0,CloudClient.TRIAL_LIMIT-used);}
    static String quota(Context c){return cache(c).contains("remaining")?"Còn "+remaining(c)+"/5 lượt · Theo lần kiểm tra gần nhất":"5 lượt Pro miễn phí · Chưa xác nhận trên máy chủ";}
    static void show(MainActivity host,UiTheme theme){
        MobileUi u=new MobileUi(host,theme);LinearLayout p=u.column();p.setPadding(u.dp(20),u.dp(8),u.dp(20),u.dp(16));
        TextView device=u.text("Mã thiết bị · "+CloudIdentity.code(host),12,false);device.setTextIsSelectable(true);
        EditText name=new EditText(host);name.setSingleLine();name.setTextColor(theme.ink);name.setHintTextColor(theme.muted);name.setTextSize(16);name.setHint("Tên hiển thị");name.setContentDescription("Tên hồ sơ");name.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(80)});name.setText(host.getSharedPreferences("profile",0).getString("name",""));p.addView(name,new LinearLayout.LayoutParams(-1,u.dp(56)));u.gap(p,12);p.addView(device);u.gap(p,20);
        TextView balance=u.text(quota(host),17,true);balance.setAccessibilityLiveRegion(android.view.View.ACCESSIBILITY_LIVE_REGION_POLITE);p.addView(balance);u.gap(p,6);p.addView(u.text("5 lượt trọn đời · 5.000 ký tự/lượt. Có thể gộp tối đa 4 lượt cho một chương, không lấy chữ chương sau.",13,false));u.gap(p,12);
        TextView state=u.text("Hồ sơ, lượt tạo và sách lưu riêng trên thiết bị. Không cần đăng nhập. Bạn có thể xuất audio để tự nghe trên máy khác.",13,false);p.addView(state);u.gap(p,12);
        Button refresh=u.button("Kiểm tra lượt Pro",false,"refresh");p.addView(refresh,new LinearLayout.LayoutParams(-1,u.dp(50)));u.gap(p,8);
        Button trial=u.button("Tạo thử với sách đang mở",true,"headphones");p.addView(trial,new LinearLayout.LayoutParams(-1,u.dp(52)));u.gap(p,8);
        Button combo=u.button("Combo 5 cuốn · 50.000đ",false,"book");p.addView(combo,new LinearLayout.LayoutParams(-1,u.dp(50)));
        ScrollView scroll=new ScrollView(host);scroll.addView(p);AlertDialog dialog=new AlertDialog.Builder(host).setTitle("Hồ sơ của bạn").setView(scroll).setPositiveButton("Lưu hồ sơ",null).setNegativeButton("Đóng",null).create();
        dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{host.getSharedPreferences("profile",0).edit().putString("name",name.getText().toString().trim()).apply();state.setText("Đã lưu hồ sơ trên thiết bị.");}));
        trial.setOnClickListener(v->{dialog.dismiss();host.appCloud();});combo.setOnClickListener(v->combo(host,theme));
        refresh.setOnClickListener(v->{String base=host.getSharedPreferences("settings",0).getString("cloudURL","");if(base.isEmpty()){state.setText("Pro Cloud chưa kết nối. Bạn vẫn có thể dùng Lite miễn phí.");return;}refresh.setEnabled(false);state.setText("Đang kiểm tra số lượt trên máy chủ…");ExecutorService io=Executors.newSingleThreadExecutor();io.submit(()->{try{JSONObject response=new CloudClient(host,base).post("profile",new JSONObject());remember(host,response,base);host.runOnUiThread(()->{if(dialog.isShowing()){balance.setText(quota(host));state.setText("Máy chủ vừa xác nhận số lượt của thiết bị này.");refresh.setEnabled(true);}});}catch(Exception e){host.runOnUiThread(()->{if(dialog.isShowing()){state.setText("Chưa xác nhận được số lượt. Các lượt đã dùng vẫn được giữ. "+(e.getMessage()==null?"":e.getMessage()));refresh.setEnabled(true);}});}finally{io.shutdown();}});});dialog.show();MobileUi.styleAlert(dialog,theme);
    }
    static void combo(MainActivity host,UiTheme theme){
        MobileUi.showAlert(host,theme,new AlertDialog.Builder(host).setTitle("Combo 5 cuốn · 50.000đ")
          .setMessage("Bản Google Play sẽ thanh toán bằng Google Play Billing; APK phát hành trực tiếp sẽ dùng QR/SePay. Hai giao dịch đều cấp quyền riêng cho thiết bị này sau khi máy chủ xác minh.\n\nƯu đãi 50.000đ/5 cuốn hiện áp dụng trên Mac. Gói và giá Android cần được cấu hình riêng trước khi bật mua.\n\nCombo Mac đã mua vẫn giữ quyền lợi và hạn dùng đã công bố; không cần mua lại chỉ để kiểm tra đơn.")
          .setPositiveButton("Đã hiểu",null));
    }
}
