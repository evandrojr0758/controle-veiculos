package br.com.dezsul.veiculos;
/** Estimates GPS distance; never writes the odometer or closes a trip automatically. */
public final class TripEngine {
 public double meters; public boolean gap;
 private boolean baseline,notified,temporary;
 private double lat,lon,anchorLat,anchorLon;
 private long lastTime,stationarySince;
 public TripEngine(double meters,boolean gap){this.meters=meters;this.gap=gap;}
 public static double distance(double a,double b,double c,double d){
  double p=Math.toRadians(c-a),q=Math.toRadians(d-b);
  double h=Math.sin(p/2)*Math.sin(p/2)+Math.cos(Math.toRadians(a))*Math.cos(Math.toRadians(c))*Math.sin(q/2)*Math.sin(q/2);
  return 6371000*2*Math.atan2(Math.sqrt(h),Math.sqrt(Math.max(0,1-h)));
 }
 public void sample(double la,double lo,float accuracy,float speed,long time){
  if(!Double.isFinite(la)||!Double.isFinite(lo)||Math.abs(la)>90||Math.abs(lo)>180||!Float.isFinite(accuracy)||accuracy<0||accuracy>25)return;
  if(baseline&&time<=lastTime)return;
  if(!baseline||time-lastTime>45000){
   if(baseline)gap=true;
   baseline=true;lat=anchorLat=la;lon=anchorLon=lo;lastTime=stationarySince=time;return;
  }
  double traveled=distance(lat,lon,la,lo),elapsed=(time-lastTime)/1000.0;
  if(traveled/elapsed>60){gap=true;return;}
  boolean moved=speed>=1.5||distance(anchorLat,anchorLon,la,lo)>35;
  if(moved){
   if(traveled>=3){meters+=traveled;lat=la;lon=lo;}
   anchorLat=la;anchorLon=lo;stationarySince=time;notified=false;temporary=false;
  }
  lastTime=time;
 }
 public boolean shouldNotify(long now){return baseline&&!notified&&!temporary&&now>=lastTime&&now-lastTime<30000&&now-stationarySince>=300000;}
 public void notificationSent(){notified=true;}
 public void temporaryStop(){temporary=true;}
 public long lastFixTime(){return lastTime;}
}
