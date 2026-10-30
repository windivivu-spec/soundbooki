package studio.windi.soundbooki;

import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.*;
import android.widget.*;
import android.app.Activity;
import android.app.Dialog;
import android.app.AlertDialog;
import android.widget.CompoundButton;
import android.widget.EditText;
import android.widget.SeekBar;
import android.widget.TextView;
import android.view.Window;
import android.view.WindowManager;
import java.util.function.IntConsumer;

/** Native mobile primitives using the existing palette and local fonts. */
final class MobileUi {
    final Context c; final UiTheme t;
    MobileUi(Context c, UiTheme theme){this.c=c;t=theme;}
    int dp(float v){return t.dp(v);}
    LinearLayout column(){LinearLayout v=new LinearLayout(c);v.setOrientation(LinearLayout.VERTICAL);return v;}
    LinearLayout row(){LinearLayout v=new LinearLayout(c);v.setGravity(Gravity.CENTER_VERTICAL);return v;}
    TextView text(String value,float size,boolean strong){TextView v=new TextView(c);v.setText(value);v.setTextSize(size);v.setTextColor(strong?t.ink:t.muted);v.setTypeface(strong?t.bold:Typeface.create("sans-serif",Typeface.NORMAL));v.setLineSpacing(dp(2),1f);return v;}
    TextView heading(String value,float size){TextView v=text(value,size,true);v.setTypeface(t.display);return v;}
    Button button(String value,boolean primary,String icon){Button b=new Button(c);b.setText(value);b.setAllCaps(false);b.setTextSize(14);b.setTypeface(t.bold);b.setTextColor(primary?Color.WHITE:t.accent);b.setBackground(t.buttonBackground(primary,16));b.setMinHeight(dp(48));b.setMinimumWidth(0);b.setMinWidth(0);b.setPadding(dp(12),0,dp(12),0);if(icon!=null){b.setCompoundDrawablesWithIntrinsicBounds(t.icon(icon,primary?Color.WHITE:t.accent,20),null,null,null);b.setCompoundDrawablePadding(dp(8));}return b;}
    ImageButton icon(String kind,String description,View.OnClickListener click){ImageButton b=new ImageButton(c);b.setImageDrawable(t.icon(kind,t.accent,22));b.setContentDescription(description);b.setBackground(t.chipBackground(t.glass,0,14));b.setOnClickListener(click);return b;}
    ArrayAdapter<String> spinnerAdapter(String[] items){
        return new ArrayAdapter<String>(c,0,items){
            private TextView row(String value,boolean dropdown){
                TextView v=text(value,14,true);v.setGravity(Gravity.CENTER_VERTICAL);v.setSingleLine(true);v.setEllipsize(android.text.TextUtils.TruncateAt.END);
                v.setPadding(dp(dropdown?16:12),dp(dropdown?12:8),dp(dropdown?16:12),dp(dropdown?12:8));
                if(dropdown){v.setMinHeight(dp(48));v.setBackground(t.chipBackground(t.surface,t.line,12));}
                return v;
            }
            @Override public View getView(int position,View convertView,android.view.ViewGroup parent){return row(getItem(position),false);}
            @Override public View getDropDownView(int position,View convertView,android.view.ViewGroup parent){return row(getItem(position),true);}
        };
    }
    void styleSpinner(Spinner spinner){
        spinner.setPopupBackgroundDrawable(t.card(t.surface,t.edge,16));
        spinner.setDropDownVerticalOffset(dp(6));
        spinner.setDropDownWidth(-1);
    }
    static Dialog options(Activity host,UiTheme theme,String title,String[] labels,IntConsumer selected){
        MobileUi ui=new MobileUi(host,theme);Dialog dialog=new Dialog(host);
        LinearLayout root=ui.column();root.setPadding(ui.dp(18),ui.dp(16),ui.dp(18),ui.dp(18));root.setBackground(theme.card(theme.surface,theme.edge,22));root.setElevation(ui.dp(12));
        LinearLayout heading=ui.row();TextView name=ui.heading(title,19);heading.addView(name,new LinearLayout.LayoutParams(0,-2,1));ImageButton close=ui.icon("close","Đóng",v->dialog.dismiss());heading.addView(close,new LinearLayout.LayoutParams(ui.dp(40),ui.dp(40)));root.addView(heading);
        ScrollView scroll=new ScrollView(host);scroll.setFillViewport(false);LinearLayout rows=ui.column();rows.setPadding(0,ui.dp(8),0,0);
        for(int i=0;i<labels.length;i++){final int index=i;TextView row=ui.text(labels[i],15,true);row.setGravity(Gravity.CENTER_VERTICAL);row.setMinHeight(ui.dp(54));row.setPadding(ui.dp(16),ui.dp(10),ui.dp(16),ui.dp(10));row.setBackground(theme.chipBackground(theme.canvas,theme.line,14));row.setFocusable(true);row.setClickable(true);LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.topMargin=ui.dp(6);rows.addView(row,lp);row.setOnClickListener(v->{dialog.dismiss();selected.accept(index);});}
        scroll.addView(rows);int maxHeight=(int)(host.getResources().getDisplayMetrics().heightPixels*.64f);int listHeight=Math.min(maxHeight,ui.dp(Math.min(labels.length,8)*60+8));root.addView(scroll,new LinearLayout.LayoutParams(-1,listHeight));
        dialog.setContentView(root);dialog.show();Window w=dialog.getWindow();if(w!=null){w.setBackgroundDrawableResource(android.R.color.transparent);w.addFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND);WindowManager.LayoutParams a=w.getAttributes();a.dimAmount=.58f;w.setAttributes(a);w.setLayout(host.getResources().getDisplayMetrics().widthPixels-ui.dp(36),WindowManager.LayoutParams.WRAP_CONTENT);w.setNavigationBarColor(theme.surface);}
        return dialog;
    }
    static AlertDialog showAlert(Activity host,UiTheme theme,AlertDialog.Builder builder){
        AlertDialog dialog=builder.create();dialog.show();styleAlert(dialog,theme);return dialog;
    }
    static void styleAlert(AlertDialog dialog,UiTheme theme){
        Window w=dialog.getWindow();if(w!=null){w.setBackgroundDrawable(theme.card(theme.surface,theme.edge,22));w.addFlags(WindowManager.LayoutParams.FLAG_DIM_BEHIND);WindowManager.LayoutParams a=w.getAttributes();a.dimAmount=.52f;w.setAttributes(a);}
        int titleId=dialog.getContext().getResources().getIdentifier("alertTitle","id","android");TextView title=titleId==0?null:dialog.findViewById(titleId);if(title!=null){title.setTextColor(theme.ink);title.setTypeface(theme.display);title.setTextSize(19);}
        TextView message=dialog.findViewById(android.R.id.message);if(message!=null){message.setTextColor(theme.muted);message.setTypeface(theme.regular);}
        for(int id:new int[]{android.R.id.button1,android.R.id.button2,android.R.id.button3}){Button b=dialog.findViewById(id);if(b!=null){b.setTextColor(theme.accent);b.setTypeface(theme.bold);b.setAllCaps(false);b.setMinHeight(theme.dp(48));}}
        View decor=dialog.getWindow()==null?null:dialog.getWindow().getDecorView();if(decor!=null)styleControls(decor,theme);
    }
    static void styleControl(View v,UiTheme theme){styleControls(v,theme);}
    private static void styleControls(View v,UiTheme theme){
        if(v instanceof EditText){EditText e=(EditText)v;e.setTextColor(theme.ink);e.setHintTextColor(theme.quiet);e.setTypeface(theme.regular);e.setBackground(theme.card(theme.canvas,theme.edge,12));}
        else if(v instanceof android.widget.Switch){android.widget.Switch s=(android.widget.Switch)v;s.setTextColor(theme.ink);s.setTypeface(theme.regular);s.setThumbTintList(android.content.res.ColorStateList.valueOf(theme.accent));s.setTrackTintList(android.content.res.ColorStateList.valueOf(theme.edge));}
        else if(v instanceof CompoundButton){CompoundButton b=(CompoundButton)v;b.setTextColor(theme.ink);b.setTypeface(theme.regular);b.setButtonTintList(android.content.res.ColorStateList.valueOf(theme.accent));}
        else if(v instanceof SeekBar){SeekBar s=(SeekBar)v;s.setProgressTintList(android.content.res.ColorStateList.valueOf(theme.accent));s.setThumbTintList(android.content.res.ColorStateList.valueOf(theme.accent));}
        if(v instanceof android.view.ViewGroup){android.view.ViewGroup g=(android.view.ViewGroup)v;for(int i=0;i<g.getChildCount();i++)styleControls(g.getChildAt(i),theme);}
    }
    LinearLayout card(){LinearLayout v=column();v.setBackground(t.card(t.surface,t.edge,20));v.setPadding(dp(16),dp(16),dp(16),dp(16));return v;}
    void gap(LinearLayout parent,int size){parent.addView(new View(c),new LinearLayout.LayoutParams(1,dp(size)));}
    void add(LinearLayout parent,View child,int height){parent.addView(child,new LinearLayout.LayoutParams(-1,height<0?height:dp(height)));}
    static String chars(int n){return n<1000?n+" ký tự":String.format(java.util.Locale.forLanguageTag("vi-VN"),"%.1fK ký tự",n/1000.0);}
    static String time(long ms){long s=Math.max(0,ms/1000);return s>=3600?String.format(java.util.Locale.ROOT,"%d:%02d:%02d",s/3600,s/60%60,s%60):String.format(java.util.Locale.ROOT,"%d:%02d",s/60,s%60);}
}
