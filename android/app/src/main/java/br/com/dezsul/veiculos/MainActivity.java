package br.com.dezsul.veiculos;
import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.location.LocationManager;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.webkit.*;
import android.widget.*;
import java.util.*;

public class MainActivity extends Activity {
 static final String HOST="controle-veiculos-jpnsn36kukknr96dv9noma.streamlit.app",HOME="https://"+HOST+"/?view=vehicles&native=android";
 WebView web;TextView status;SharedPreferences prefs;Uri requested;String lastCommand="";
 Handler ui=new Handler(Looper.getMainLooper());
 final Runnable refresh=new Runnable(){public void run(){updateStatus();ui.postDelayed(this,3000);}};
 public void onCreate(Bundle state){
  super.onCreate(state);prefs=getSharedPreferences(TrackingService.PREFS,MODE_PRIVATE);
  LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setBackgroundColor(Color.WHITE);
  layout.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets.consumeSystemWindowInsets();});
  status=new TextView(this);status.setPadding(20,12,20,12);status.setTextColor(Color.rgb(8,61,109));layout.addView(status);
  web=new WebView(this);layout.addView(web,new LinearLayout.LayoutParams(-1,0,1));
  LinearLayout buttons=new LinearLayout(this);
  Button home=new Button(this);home.setText("Sistema");home.setOnClickListener(v->web.loadUrl(prefs.getBoolean("pending",false)?returnUrl():HOME));
  Button end=new Button(this);end.setText("Finalizar viagem");end.setOnClickListener(v->{if(prefs.getBoolean("active",false))confirmFinish();else Toast.makeText(this,"Nenhuma viagem com GPS aberta",Toast.LENGTH_SHORT).show();});
  buttons.addView(home,new LinearLayout.LayoutParams(0,-2,1));buttons.addView(end,new LinearLayout.LayoutParams(0,-2,1));layout.addView(buttons);setContentView(layout);
  web.getSettings().setJavaScriptEnabled(true);web.getSettings().setDomStorageEnabled(true);
  web.getSettings().setAllowFileAccess(false);web.getSettings().setAllowContentAccess(false);web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
  CookieManager.getInstance().setAcceptCookie(true);
  web.setWebViewClient(new WebViewClient(){
   public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){
    Uri u=r.getUrl();
    if(trusted(u.toString())&&u.getQueryParameter("native_command")!=null){if(r.isForMainFrame()&&trusted(v.getUrl()))command(u);return true;}
    if(trusted(u.toString()))return false;
    if("https".equals(u.getScheme())&&r.hasGesture())startActivity(new Intent(Intent.ACTION_VIEW,u));return true;
   }
   public void onPageFinished(WebView v,String url){
    if(!trusted(url))return;
    // Intercept only commands at the allowed top-level HTTPS origin; no JS interface exposed to frames.
    v.evaluateJavascript("(()=>{if(window.__gpsObserver)return;window.__gpsObserver=true;let seen='';const run=()=>{const a=document.querySelector('a[data-gps-command]');if(a&&a.href!==seen){seen=a.href;location.href=a.href;}};new MutationObserver(run).observe(document.body,{childList:true,subtree:true});run();})()",null);
   }
  });
  web.loadUrl(prefs.getBoolean("pending",false)?returnUrl():HOME);handleIntent(getIntent());ui.post(refresh);
  long heartbeat=prefs.getLong("heartbeat",0);boolean recent=heartbeat>0&&SystemClock.elapsedRealtime()>=heartbeat&&SystemClock.elapsedRealtime()-heartbeat<30000;
  if(prefs.getBoolean("active",false)&&!prefs.getBoolean("pending",false)&&!recent&&!getIntent().getBooleanExtra("finish",false)){
   new AlertDialog.Builder(this).setTitle("Viagem em andamento").setMessage("Retomar a contagem do GPS? Se o Android interrompeu o serviço, confira o hodômetro no retorno.")
    .setPositiveButton("Retomar",(d,w)->{prefs.edit().putBoolean("gap",true).apply();requested=null;permissions();})
    .setNegativeButton("Finalizar",(d,w)->confirmFinish()).show();
  }
 }
 boolean trusted(String url){if(url==null)return false;Uri u=Uri.parse(url);return "https".equals(u.getScheme())&&HOST.equals(u.getHost())&&(u.getPort()==-1||u.getPort()==443);}
 void command(Uri u){
  String id=u.getQueryParameter("id");if(id==null||id.isEmpty())return;
  if("complete".equals(u.getQueryParameter("native_command"))){
   if(id.equals(prefs.getString("id",""))){stopService(new Intent(this,TrackingService.class));prefs.edit().clear().commit();lastCommand="";updateStatus();}return;
  }
  if(!"start".equals(u.getQueryParameter("native_command"))||u.toString().equals(lastCommand))return;lastCommand=u.toString();
  if(prefs.getBoolean("active",false)){
   if(!id.equals(prefs.getString("id","")))new AlertDialog.Builder(this).setMessage("Existe outra viagem aberta no GPS. Finalize antes de iniciar esta.").setPositiveButton("OK",null).show();return;
  }
  String plate=u.getQueryParameter("plate"),initial=u.getQueryParameter("initial");
  try{if(plate==null||!plate.matches("[A-Z0-9]{7}")||Long.parseLong(initial)<0)return;}catch(Exception e){return;}
  requested=u;
  new AlertDialog.Builder(this).setTitle("Contar quilômetros por GPS").setMessage("Iniciar a contagem para "+plate+"? Ela continua com a tela bloqueada e avisa após 5 minutos parado. Finalize ao retornar.")
   .setPositiveButton("Iniciar GPS",(d,w)->permissions()).setNegativeButton("Agora não",(d,w)->{requested=null;lastCommand="";}).show();
 }
 void permissions(){
  ArrayList<String> need=new ArrayList<>();
  if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED){need.add(Manifest.permission.ACCESS_COARSE_LOCATION);need.add(Manifest.permission.ACCESS_FINE_LOCATION);}
  if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)need.add(Manifest.permission.POST_NOTIFICATIONS);
  if(!need.isEmpty())requestPermissions(need.toArray(new String[0]),1);else begin();
 }
 public void onRequestPermissionsResult(int r,String[] p,int[] g){super.onRequestPermissionsResult(r,p,g);if(r==1)begin();}
 void begin(){
  NotificationManager n=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
  if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED||!n.areNotificationsEnabled()||!((LocationManager)getSystemService(LOCATION_SERVICE)).isProviderEnabled(LocationManager.GPS_PROVIDER)){
   lastCommand="";new AlertDialog.Builder(this).setMessage("Ative localização precisa, GPS e notificações para contar os quilômetros e receber o aviso de parada.")
    .setPositiveButton("Configurações",(d,w)->startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName())))).setNegativeButton("Fechar",null).show();return;
  }
  if(requested!=null){
   prefs.edit().clear().putString("id",requested.getQueryParameter("id")).putString("plate",requested.getQueryParameter("plate")).putLong("initial",Long.parseLong(requested.getQueryParameter("initial"))).putBoolean("active",true).putBoolean("pending",false).commit();requested=null;
  }
  startForegroundService(new Intent(this,TrackingService.class));updateStatus();
 }
 public void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);handleIntent(intent);}
 void handleIntent(Intent i){if(i.getBooleanExtra("finish",false)&&prefs.getBoolean("active",false)&&prefs.getString("id","").equals(i.getStringExtra("trip_id")))confirmFinish();}
 void confirmFinish(){
  new AlertDialog.Builder(this).setTitle("Finalizar viagem?").setMessage("Encerrar a contagem e abrir a confirmação do KM de retorno?")
   .setPositiveButton("Finalizar viagem",(d,w)->{prefs.edit().putBoolean("pending",true).commit();stopService(new Intent(this,TrackingService.class));new Handler(Looper.getMainLooper()).postDelayed(()->web.loadUrl(returnUrl()),300);})
   .setNegativeButton("Parada temporária",(d,w)->{if(!prefs.getBoolean("pending",false))startService(new Intent(this,TrackingService.class).setAction(TrackingService.TEMP));}).show();
 }
 String returnUrl(){
  double m=Double.longBitsToDouble(prefs.getLong("meters",0));
  return Uri.parse(HOME).buildUpon().appendQueryParameter("plate",prefs.getString("plate","")).appendQueryParameter("gps_id",prefs.getString("id",""))
   .appendQueryParameter("gps_km",String.format(Locale.US,"%.3f",m/1000)).appendQueryParameter("gps_gap",prefs.getBoolean("gap",false)?"1":"0").appendQueryParameter("gps_return","1").build().toString();
 }
 void updateStatus(){
  if(!prefs.getBoolean("active",false)){status.setText("10 SUL • Registre a saída para iniciar o GPS");return;}
  double m=Double.longBitsToDouble(prefs.getLong("meters",0));status.setText(prefs.getString("plate","")+" • "+String.format(Locale.getDefault(),"%.2f km estimados",m/1000)+(prefs.getBoolean("pending",false)?" • confirme o retorno":" • viagem aberta"));
 }
 public void onBackPressed(){if(web.canGoBack())web.goBack();else super.onBackPressed();}
 public void onDestroy(){ui.removeCallbacksAndMessages(null);web.destroy();super.onDestroy();}
}
