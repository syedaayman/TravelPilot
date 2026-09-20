import React from 'react';
import { ExternalLink, MapPin, Star, Utensils, Landmark, Palette, Shirt, Theater, ShoppingBag, Hotel, Car, Sparkles, Footprints, Clock } from 'lucide-react';
import type { TripDetailResponse } from '../../types';

type StopType = TripDetailResponse['stops'][0];
type ItineraryItemType = TripDetailResponse['itinerary'][0];

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  Food: <Utensils className="w-3.5 h-3.5 text-blue-600" />,
  Restaurant: <Utensils className="w-3.5 h-3.5 text-blue-600" />,
  Heritage: <Landmark className="w-3.5 h-3.5 text-blue-600" />,
  historical: <Landmark className="w-3.5 h-3.5 text-blue-600" />,
  Museum: <Landmark className="w-3.5 h-3.5 text-blue-600" />,
  museum: <Landmark className="w-3.5 h-3.5 text-blue-600" />,
  Textiles: <Shirt className="w-3.5 h-3.5 text-blue-600" />,
  Craft: <Palette className="w-3.5 h-3.5 text-blue-600" />,
  Culture: <Theater className="w-3.5 h-3.5 text-blue-600" />,
  cultural: <Theater className="w-3.5 h-3.5 text-blue-600" />,
  Shopping: <ShoppingBag className="w-3.5 h-3.5 text-blue-600" />,
  shopping: <ShoppingBag className="w-3.5 h-3.5 text-blue-600" />,
  Beach: <Sparkles className="w-3.5 h-3.5 text-blue-600" />,
  beach: <Sparkles className="w-3.5 h-3.5 text-blue-600" />,
  Nature: <Sparkles className="w-3.5 h-3.5 text-blue-600" />,
  nature: <Sparkles className="w-3.5 h-3.5 text-blue-600" />,
  Hotel: <Hotel className="w-3.5 h-3.5 text-blue-600" />,
  Transport: <Car className="w-3.5 h-3.5 text-blue-600" />,
};

function getCategoryIcon(cat?: string | null, title?: string | null) {
  if (!cat && title) {
    const t = title.toLowerCase();
    if (t.includes('breakfast') || t.includes('lunch') || t.includes('dinner') || t.includes('biryani') || t.includes('chai')) return <Utensils className="w-3.5 h-3.5 text-blue-600" />;
    if (t.includes('walk') || t.includes('trek')) return <Footprints className="w-3.5 h-3.5 text-blue-600" />;
    if (t.includes('fort') || t.includes('palace') || t.includes('temple') || t.includes('tomb') || t.includes('charminar')) return <Landmark className="w-3.5 h-3.5 text-blue-600" />;
    if (t.includes('market') || t.includes('bazaar') || t.includes('shopping')) return <ShoppingBag className="w-3.5 h-3.5 text-blue-600" />;
    if (t.includes('textile') || t.includes('ikat') || t.includes('saree') || t.includes('print')) return <Shirt className="w-3.5 h-3.5 text-blue-600" />;
  }
  return CATEGORY_ICONS[cat || ''] || <Sparkles className="w-3.5 h-3.5 text-blue-600" />;
}

function getDayTheme(items: ItineraryItemType[], destName: string, dayNum: number) {
  const cats = Array.from(new Set(items.map(i => i.category).filter(Boolean)));
  const primaryCats = cats.slice(0, 3).join(' · ') || 'Heritage · Food · Culture';
  return {
    badge: primaryCats,
    summary: `Day ${dayNum} in ${destName}: ${primaryCats}`
  };
}

export function DayItinerary({ stop, items }: { stop: StopType; items: ItineraryItemType[] }) {
  const daysMap = new Map<number, ItineraryItemType[]>();
  items.forEach(item => daysMap.set(item.day_number, [...(daysMap.get(item.day_number) || []), item]));
  
  const days = Array.from(daysMap.entries())
    .map(([day_number, dayItems]) => ({ 
      day_number, 
      items: dayItems.sort((a, b) => a.start_time.localeCompare(b.start_time)) 
    }))
    .sort((a, b) => a.day_number - b.day_number);

  return (
    <div className="space-y-6">
      {days.map(day => {
        const theme = getDayTheme(day.items, stop.destination_name, day.day_number);
        const daySpend = day.items.reduce((sum, i) => sum + (i.cost || 0), 0);
        const totalTravelMin = day.items.reduce((sum, i) => sum + (i.travel_time_from_prev_minutes || 0), 0);
        const totalDistKm = day.items.reduce((sum, i) => sum + (i.travel_distance_km || 0), 0);
        const dateStr = day.items[0]?.scheduled_date || stop.arrival_date;

        return (
          <div key={day.day_number} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {/* Context Header */}
            <div className="bg-slate-50 p-4 sm:p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-md bg-blue-600 text-white text-xs font-mono font-bold">
                    DAY {day.day_number}
                  </span>
                  <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">{dateStr} · {stop.destination_name}</span>
                </div>
                <h4 className="text-base font-bold text-slate-900 mt-1">{theme.summary}</h4>
              </div>

              <div className="shrink-0 flex flex-wrap items-center gap-2">
                {totalDistKm > 0 && (
                  <span className="px-2.5 py-1 rounded-md bg-white border border-slate-200 text-slate-600 text-xs font-mono">
                    🚗 {totalDistKm.toFixed(1)} km · {totalTravelMin} min
                  </span>
                )}
                {daySpend > 0 && (
                  <span className="px-2.5 py-1 rounded-md bg-blue-50 border border-blue-200 text-blue-700 text-xs font-mono font-bold">
                    ₹{daySpend.toLocaleString()}
                  </span>
                )}
                <span className="px-3 py-1 rounded-md bg-white border border-slate-200 text-slate-700 text-xs font-medium">
                  {theme.badge}
                </span>
              </div>
            </div>

            {/* Timeline Items */}
            <div className="p-5 sm:p-6 space-y-5">
              {day.items.map((item) => {
                const icon = getCategoryIcon(item.category, item.custom_title);

                return (
                  <article key={item.id} className="relative pl-6 border-l-2 border-blue-200 hover:border-blue-600 transition-colors group">
                    {/* Circle Node */}
                    <div className="absolute -left-[7px] top-1.5 w-3 h-3 rounded-full bg-blue-600 border-2 border-white ring-2 ring-blue-100 group-hover:scale-125 transition-transform" />

                    {/* Transfer distance / time pill if present */}
                    {item.travel_time_from_prev_minutes > 0 && (
                      <div className="mb-2 inline-flex items-center gap-1.5 text-[11px] font-mono font-medium text-slate-500 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-full">
                        <Car className="w-3 h-3 text-slate-500" />
                        <span>{item.travel_time_from_prev_minutes} min transit</span>
                        {item.travel_distance_km && (
                          <span className="text-slate-400">({item.travel_distance_km.toFixed(1)} km)</span>
                        )}
                      </div>
                    )}

                    {/* Activity Item Box */}
                    <div className="bg-slate-50/50 hover:bg-blue-50/30 border border-slate-200 hover:border-blue-200 rounded-xl p-4 transition-all space-y-2">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold font-mono text-blue-700 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-100 flex items-center gap-1">
                            <Clock className="w-3 h-3 text-blue-600" />
                            {item.start_time} - {item.end_time}
                          </span>
                          <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-white border border-slate-200 text-slate-700 flex items-center gap-1">
                            {icon}
                            {item.category || item.item_type}
                          </span>
                        </div>

                        {item.cost && item.cost > 0 ? (
                          <span className="text-xs font-mono font-bold text-slate-700">
                            ₹{item.cost.toLocaleString()}
                          </span>
                        ) : (
                          <span className="text-xs text-slate-400 font-mono">Free Entry / Included</span>
                        )}
                      </div>

                      <div>
                        <h5 className="text-base font-bold text-slate-900">
                          {item.custom_title}
                        </h5>

                        {item.description && (
                          <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                            {item.description}
                          </p>
                        )}
                      </div>

                      {/* Item Metadata (Rating, Map Link) */}
                      <div className="flex items-center gap-4 text-xs text-slate-500 pt-1 border-t border-slate-100">
                        {(item as any).rating && (
                          <span className="flex items-center gap-1 text-amber-600 font-semibold">
                            <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                            {(item as any).rating} rating
                          </span>
                        )}
                        {(item as any).location && (
                          <span className="flex items-center gap-1 text-slate-500">
                            <MapPin className="w-3.5 h-3.5 text-slate-400" />
                            {(item as any).location}
                          </span>
                        )}
                        {(item as any).map_url && (
                          <a
                            href={(item as any).map_url}
                            target="_blank"
                            rel="noreferrer"
                            className="ml-auto text-blue-600 hover:underline font-medium flex items-center gap-1"
                          >
                            Map <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>

                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
