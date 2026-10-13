package br.com.dezsul.veiculos;
public class TripEngineTest {
 static void check(boolean ok,String message){if(!ok)throw new AssertionError(message);}
 public static void main(String[] args){
  TripEngine parked=new TripEngine(0,false);
  for(int t=0;t<=300000;t+=5000)parked.sample(-19+(t%3)*0.00001,-40,10,0,t);
  check(parked.meters==0,"Parked GPS drift");check(parked.shouldNotify(300000),"Five-minute stop alert");
  parked.notificationSent();check(!parked.shouldNotify(305000),"Do not repeat alert");
  parked.temporaryStop();check(!parked.shouldNotify(310000),"Temporary stop remains open");
  parked.sample(-18.999,-40,10,10,305000);check(parked.meters>90,"Resume after temporary stop");
  for(int t=310000;t<=605000;t+=5000)parked.sample(-18.999,-40,10,0,t);
  check(parked.shouldNotify(605000),"Alert on next stop");
  TripEngine gap=new TripEngine(12,false);gap.sample(-19,-40,5,0,0);gap.sample(-18.99,-40,5,10,60000);
  check(gap.meters==12&&gap.gap,"Do not invent distance across missing GPS");check(!gap.shouldNotify(400000),"Stale GPS cannot mean parked");
  TripEngine jump=new TripEngine(0,false);jump.sample(-19,-40,5,0,0);jump.sample(-18,-40,5,10,5000);
  check(jump.meters==0&&jump.gap,"Reject impossible jumps");jump.sample(-18.9995,-40,50,10,10000);check(jump.meters==0,"Reject inaccurate fixes");
  TripEngine trip=new TripEngine(0,false);trip.sample(-19,-40,5,10,0);trip.sample(-18.999,-40,5,10,10000);trip.sample(-19,-40,5,10,20000);
  check(trip.meters>210&&trip.meters<230,"Outbound and return distance");
  double before=trip.meters;trip.sample(-18.999,-40,5,10,15000);check(trip.meters==before,"Ignore out-of-order fixes");
  System.out.println("PASS: parked drift, stop alert, temporary stop, resumed travel, missing GPS, jumps, accuracy, round trip, stale fixes");
 }
}
