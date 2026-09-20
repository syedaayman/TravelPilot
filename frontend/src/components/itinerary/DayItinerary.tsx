import { Card, CardHeader, CardTitle, CardContent } from '../common/Card';
import { Badge } from '../common/Badge';
import type { TripDetailResponse } from '../../types';

type StopType = TripDetailResponse['stops'][0];
type ItineraryItemType = TripDetailResponse['itinerary'][0] & {
  place?: { name: string; category?: string };
  restaurant?: { name: string; cuisine?: string };
};

export function DayItinerary({ stop, items }: { stop: StopType; items: ItineraryItemType[] }) {
  // Group items by day_number
  const daysMap = new Map<number, ItineraryItemType[]>();
  items.forEach(item => {
    if (!daysMap.has(item.day_number)) {
      daysMap.set(item.day_number, []);
    }
    daysMap.get(item.day_number)!.push(item);
  });
  
  const days = Array.from(daysMap.entries())
    .map(([day_number, dayItems]) => ({
      day_number,
      items: dayItems.sort((a, b) => a.start_time.localeCompare(b.start_time))
    }))
    .sort((a, b) => a.day_number - b.day_number);

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>{stop.destination_name}</CardTitle>
        <p className="text-sm text-muted-foreground">
           {stop.arrival_date} to {stop.departure_date}
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-8">
          {days.map((day) => (
             <div key={day.day_number}>
               <h4 className="font-semibold text-lg mb-4 border-b pb-2">Day {day.day_number}</h4>
               <div className="space-y-6">
                 {day.items.map((item) => (
                    <div key={item.id} className="relative pl-6 border-l-2 border-muted">
                       <div className="absolute -left-[9px] top-1 w-4 h-4 rounded-full bg-primary" />
                       <div className="flex justify-between items-start">
                         <div>
                            <div className="font-medium text-base">
                              {item.start_time} - {item.end_time} • {item.place?.name || item.restaurant?.name || item.custom_title}
                            </div>
                            <div className="text-sm text-muted-foreground mt-1">
                               {item.place?.category || item.restaurant?.cuisine || item.item_type}
                            </div>
                            {item.travel_time_from_prev_minutes > 0 && (
                               <div className="text-xs text-blue-600 mt-2 flex items-center">
                                 ↓ {item.travel_time_from_prev_minutes} min travel
                               </div>
                            )}
                         </div>
                         <div className="text-right">
                            <Badge variant="outline">₹{item.cost}</Badge>
                         </div>
                       </div>
                    </div>
                 ))}
               </div>
             </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
