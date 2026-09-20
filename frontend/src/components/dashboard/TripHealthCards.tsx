import { Card, CardContent } from '../common/Card';
import { Badge } from '../common/Badge';

export function TripHealthCards({ trip }: { trip: any }) {
  const budget = trip.total_budget;
  const cost = trip.stops.reduce((acc: number, stop: any) => acc + stop.stop_budget, 0) +
               trip.transport_legs.reduce((acc: number, leg: any) => acc + leg.cost, 0);
  const remaining = budget - cost;

  const totalDays = trip.stops.reduce((acc: number, s: any) => acc + (s.itinerary?.length || 0), 0);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <Card>
        <CardContent className="pt-6">
          <div className="text-sm font-medium text-muted-foreground">Budget</div>
          <div className="text-2xl font-bold">₹{budget.toLocaleString()}</div>
          <div className="text-sm text-muted-foreground mt-1">
            Cost: ₹{cost.toLocaleString()}
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent className="pt-6">
          <div className="text-sm font-medium text-muted-foreground">Remaining</div>
          <div className="text-2xl font-bold">₹{remaining.toLocaleString()}</div>
          <div className="mt-1">
             <Badge variant={remaining >= 0 ? "success" : "destructive"}>
               {remaining >= 0 ? "Under Budget" : "Over Budget"}
             </Badge>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent className="pt-6">
          <div className="text-sm font-medium text-muted-foreground">Trip Health</div>
          <div className="text-2xl font-bold capitalize">{trip.status}</div>
          <div className="text-sm text-muted-foreground mt-1">
            {totalDays} Days • {trip.stops.length} Destinations
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
