package studio.windi.soundbooki;

import android.content.Context;
import android.view.*;
import android.widget.*;

/** Native responsive reading banner. Android purchase terms remain in ProfileDialog. */
final class ReadingBanner extends LinearLayout {
    private final UiTheme theme;
    private final LinearLayout copy;
    private final BannerBooksView art;
    private boolean wide;
    private final boolean compact;
    ReadingBanner(Context context,UiTheme theme,Runnable open){
        super(context);this.theme=theme;compact=getResources().getConfiguration().screenHeightDp<480;
        MobileUi ui=new MobileUi(context,theme);setTag("reading-banner");setOrientation(HORIZONTAL);setGravity(Gravity.CENTER_VERTICAL);
        setPadding(ui.dp(16),ui.dp(10),ui.dp(16),ui.dp(10));setBackground(theme.card(theme.launchBg,theme.launchRule,20));
        copy=ui.column();TextView title=ui.heading("Một trang sách.",16);title.setTextColor(theme.launchInk);copy.addView(title);ui.gap(copy,6);
        Button action=ui.button("Thêm sách",true,null);action.setOnClickListener(v->open.run());copy.addView(action,new LayoutParams(-2,-2));
        addView(copy,new LayoutParams(0,-2,1.05f));art=new BannerBooksView(context,theme);art.setTag("banner-books-vector");addView(art,new LayoutParams(0,ui.dp(compact?96:112),.95f));
    }
    @Override protected void onMeasure(int widthSpec,int heightSpec){
        boolean next=MeasureSpec.getSize(widthSpec)>=theme.dp(560);
        if(next!=wide){wide=next;setGravity(Gravity.CENTER_VERTICAL);
            copy.setLayoutParams(new LayoutParams(0,-2,wide?1:1.05f));art.setLayoutParams(new LayoutParams(0,theme.dp(compact?96:112),wide?1.15f:.95f));
        }
        super.onMeasure(widthSpec,heightSpec);
    }
}
