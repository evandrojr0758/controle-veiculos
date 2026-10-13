package br.com.dezsul.veiculos;
import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.location.*;
import android.os.*;
import java.util.Locale;

public class TrackingService extends Service implements LocationListener {
 static final String PREFS="trip",TEMP="temporary",LIVE="gps_live",STOP="gps_stop";
 TripEngine engine;SharedPreferences prefs;LocationManager locations;NotificationManager notifications;
 Handler handler=new Handler(Looper.getMainLooper());boolean listening;long startedAt;
 final Runnable tick=new Runnable(){public void run(){
  if(engine!=null){
   long at=SystemClock.elapsedRealtime();
   if((engine.lastFixTime()==0&&at-startedAt>30000)||(engine.lastFixTime()>0&&at-engine.lastFixTime()>45000)){engine.gap=true;prefs.edit().putBoolean("gap",true).apply();}
   if(engine.shouldNotify(at)){notifyStop();engine.notificationSent();}
   notifications.notify(1,liveNotification());
  }
  handler.postDelayed(this,10000);
 }};
 public void onCreate(){
  super.onCreate();prefs=getSharedPreferences(PREFS,MODE_PRIVATE);locations=(LocationManager)getSystemService(LOCATION_SERVICE);notifications=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
  notifications.createNotificationChannel(new NotificationChannel(LIVE,"Contagem de quilômetros",NotificationManager.IMPORTANCE_LOW));
  NotificationChannel stop=new NotificationChannel(STOP,"Confirmar parada da viagem",NotificationManager.IMPORTANCE_HIGH);
  stop.setDescription("Pergunta após 5 minutos parado se a viagem terminou");stop.enableVibration(true);notifications.createNotificationChannel(stop);
 }
 public int onStartCommand(Intent intent,int flags,int id){
  if(intent!=null&&TEMP.equals(intent.getAction())){if(engine!=null)engine.temporaryStop();else stopSelf();notifications.cancel(2);return START_NOT_STICKY;}
  if(!prefs.getBoolean("active",false)||prefs.getBoolean("pending",false)||checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED){stopSelf();return START_NOT_STICKY;}
  if(engine!=null)return START_NOT_STICKY;
  startedAt=SystemClock.elapsedRealtime();engine=new TripEngine(Double.longBitsToDouble(prefs.getLong("meters",0)),prefs.getBoolean("gap",false));
  if(Build.VERSION.SDK_INT>=29)startForeground(1,liveNotification(),ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION);else startForeground(1,liveNotification());
  try{locations.requestLocationUpdates(LocationManager.GPS_PROVIDER,5000,0,this,Looper.getMainLooper());listening=true;handler.post(tick);}
  catch(SecurityException|IllegalArgumentException e){prefs.edit().putBoolean("gap",true).apply();stopSelf();}
  return START_NOT_STICKY;
 }
 PendingIntent open(boolean finish){
  Intent i=new Intent(this,MainActivity.class).putExtra("finish",finish).putExtra("trip_id",prefs.getString("id",""));i.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP);
  return PendingIntent.getActivity(this,finish?21:20,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
 }
 Notification liveNotification(){
  double m=engine==null?0:engine.meters;
  boolean stale=engine==null||engine.lastFixTime()==0||SystemClock.elapsedRealtime()-engine.lastFixTime()>30000;
  return new Notification.Builder(this,LIVE).setSmallIcon(R.drawable.ic_car)
   .setContentTitle(prefs.getString("plate","")+" • "+String.format(Locale.getDefault(),"%.2f km por GPS",m/1000))
   .setContentText(stale?"Aguardando sinal GPS. Abra para conferir.":"Viagem aberta • finalize ao retornar")
   .setOngoing(true).setContentIntent(open(false)).addAction(new Notification.Action.Builder(null,"Finalizar viagem",open(true)).build()).build();
 }
 void notifyStop(){
  PendingIntent p=PendingIntent.getService(this,22,new Intent(this,TrackingService.class).setAction(TEMP),PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
  notifications.notify(2,new Notification.Builder(this,STOP).setSmallIcon(R.drawable.ic_car).setContentTitle("Você finalizou a viagem?")
   .setContentText(prefs.getString("plate","")+" está parado há 5 minutos").setContentIntent(open(true)).setAutoCancel(true)
   .addAction(new Notification.Action.Builder(null,"Finalizar viagem",open(true)).build()).addAction(new Notification.Action.Builder(null,"Parada temporária",p).build()).build());
 }
 public void onLocationChanged(Location l){
  if(engine==null||!l.hasAccuracy())return;
  engine.sample(l.getLatitude(),l.getLongitude(),l.getAccuracy(),l.hasSpeed()?l.getSpeed():-1,l.getElapsedRealtimeNanos()/1000000);
  prefs.edit().putLong("meters",Double.doubleToRawLongBits(engine.meters)).putBoolean("gap",engine.gap).putLong("heartbeat",SystemClock.elapsedRealtime()).apply();
 }
 public void onProviderEnabled(String p){}
 public void onProviderDisabled(String p){if(engine!=null){engine.gap=true;prefs.edit().putBoolean("gap",true).apply();}}
 public void onStatusChanged(String p,int s,Bundle b){}
 public void onDestroy(){
  handler.removeCallbacksAndMessages(null);if(listening)locations.removeUpdates(this);
  if(engine!=null)prefs.edit().putLong("meters",Double.doubleToRawLongBits(engine.meters)).putBoolean("gap",engine.gap).putLong("heartbeat",0).commit();
  notifications.cancel(2);super.onDestroy();
 }
 public IBinder onBind(Intent i){return null;}
}
