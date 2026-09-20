import { Card, CardContent } from '../common/Card';
import { Wallet, ShieldCheck, Calendar, Sparkles } from 'lucide-react';


export function TripHealthCards({ trip }: { trip: any }) {
  const budget = trip.total_budget || 0;
  
  let cost = 0;
  if (trip.stops) {
    cost += trip.stops.reduce((acc: number, s: any) => {
      const stopCost = s.stop_budget || 0;
      const hotelCost = s.hotel?.price_per_night ? s.hotel.price_per_night * (s.duration_days || 1) : 0;
      return acc + stopCost + hotelCost;
    }, 0);
  }
  if (trip.transport_legs) {
    cost += trip.transport_legs.reduce((acc: number, leg: any) => acc + (leg.cost || leg.price || 0), 0);
  }

  const remaining = budget - cost;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card className="bg-white border-slate-200 shadow-sm">
        <CardContent className="p-5 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <Wallet className="w-3.5 h-3.5 text-blue-600" /> Total Budget Cap
            </div>
            <div className="text-2xl font-black font-mono text-slate-900">
              ₹{budget.toLocaleString()}
            </div>
            <div className="text-xs text-slate-500 mt-1 font-mono">
              Est. Cost: ₹{cost.toLocaleString()}
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
            <Wallet className="w-6 h-6" />
          </div>
        </CardContent>
      </Card>
      
      <Card className="bg-white border-slate-200 shadow-sm">
        <CardContent className="p-5 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
              Budget Remaining
            </div>
            <div className={`text-2xl font-black font-mono ${remaining >= 0 ? 'text-blue-700' : 'text-rose-600'}`}>
              ₹{Math.abs(remaining).toLocaleString()}
            </div>
            <div className="mt-1">
              <span className={`inline-flex items-center text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                remaining >= 0
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200'
              }`}>
                {remaining >= 0 ? '✓ Within Budget Limit' : '⚠ Over-Allocation'}
              </span>
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </CardContent>
      </Card>
      
      <Card className="bg-white border-slate-200 shadow-sm">
        <CardContent className="p-5 flex items-center justify-between">
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" /> Feasibility Index
            </div>
            <div className="text-2xl font-black text-slate-900 capitalize flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              {trip.status === 'planned' ? 'Feasible' : trip.status}
            </div>
            <div className="text-xs text-slate-500 mt-1 font-medium">
              {trip.duration_days || trip.stops.length} Days · {trip.stops.length} Destinations
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600">
            <Calendar className="w-6 h-6" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
