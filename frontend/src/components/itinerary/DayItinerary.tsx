import { ExternalLink, MapPin, Star } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../common/Card';
import { Badge } from '../common/Badge';
import type { TripDetailResponse } from '../../types';

type StopType = TripDetailResponse['stops'][0];
type ItineraryItemType = TripDetailResponse['itinerary'][0] & {
  place?: { name: string; category?: string };
  restaurant?: { name: string; cuisine?: string };
};

export function DayItinerary({ stop, items }: { stop: StopType; items: ItineraryItemType[] }) {
  const daysMap = new Map<number, ItineraryItemType[]>();
  items.forEach(item => daysMap.set(item.day_number, [...(daysMap.get(item.day_number) || []), item]));
  const days = Array.from(daysMap.entries())
    .map(([day_number, dayItems]) => ({ day_number, items: dayItems.sort((a, b) => a.start_time.localeCompare(b.start_time)) }))
    .sort((a, b) => a.day_number - b.day_number);

  return (
    <Card className="mb-6 overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-indigo-50 to-white">
        <CardTitle>{stop.destination_name}</CardTitle>
        <p className="text-sm text-muted-foreground">{stop.arrival_date} to {stop.departure_date}</p>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="space-y-8">
          {days.map(day => (
            <section key={day.day_number}>
              <h4 className="mb-4 border-b pb-2 text-lg font-semibold">Day {day.day_number}</h4>
              <div className="space-y-6">
                {day.items.map(item => (
                  <article key={item.id} className="relative border-l-2 border-indigo-200 pl-6">
                    <div className="absolute -left-[9px] top-1 h-4 w-4 rounded-full bg-indigo-600 ring-4 ring-indigo-50" />
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-slate-900">{item.start_time} – {item.end_time} · {item.place?.name || item.restaurant?.name || item.custom_title}</p>
                        <p className="mt-1 text-sm capitalize text-slate-500">{item.category || item.place?.category || item.restaurant?.cuisine || item.item_type}</p>
                        {item.description && <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>}
                        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
                          {item.rating && <span className="inline-flex items-center gap-1 font-semibold text-amber-600"><Star className="h-3.5 w-3.5 fill-current" />{item.rating}</span>}
                          {item.map_url && <a href={item.map_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-indigo-600 hover:text-indigo-800"><MapPin className="h-3.5 w-3.5" />Open in Maps <ExternalLink className="h-3 w-3" /></a>}
                          {item.travel_time_from_prev_minutes > 0 && <span className="text-blue-600">{item.travel_time_from_prev_minutes} min from the previous stop</span>}
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <Badge variant="outline">₹{item.cost}</Badge>
                        {item.image_url && <img src={item.image_url} alt={item.custom_title || 'Planned activity'} className="mt-3 h-20 w-28 rounded-lg object-cover shadow-sm" loading="lazy" />}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
