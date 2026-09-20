import React, { useState, useEffect } from 'react';
import { Utensils, Star, Flame, Sparkles, MapPin } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../common/Card';
import { getDestinationCulture } from '../../api/destinations';

interface FoodDiscoveryCardProps {
  stops: any[];
}

export const FoodDiscoveryCard: React.FC<FoodDiscoveryCardProps> = ({ stops }) => {
  const [activeStopIndex, setActiveStopIndex] = useState(0);
  const [cultureData, setCultureData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const activeStop = stops[activeStopIndex] || stops[0];

  useEffect(() => {
    if (!activeStop) return;
    setLoading(true);
    getDestinationCulture(activeStop.destination_id || activeStop.destination_name)
      .then(res => setCultureData(res.culture || res))
      .catch(() => setCultureData(null))
      .finally(() => setLoading(false));
  }, [activeStopIndex, activeStop]);

  if (!stops || stops.length === 0) return null;

  const food = cultureData?.food || {};
  const signatureDishes = food.signature_dishes || [];
  const diningSpots = food.recommended_dining || [];

  return (
    <Card className="bg-white border-slate-200 shadow-sm">
      <CardHeader className="p-5 border-b border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-50/50">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <Utensils className="w-5 h-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-slate-900">
              Must-Try Regional Food & Gastronomy
            </CardTitle>
            <p className="text-xs text-slate-500">
              Authentic culinary heritage & signature regional flavors
            </p>
          </div>
        </div>

        {/* Destination Tabs */}
        <div className="flex gap-1.5 bg-slate-100 p-1 rounded-lg border border-slate-200">
          {stops.map((stop: any, idx: number) => (
            <button
              key={stop.id || idx}
              onClick={() => setActiveStopIndex(idx)}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${
                activeStopIndex === idx
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              {stop.destination_name}
            </button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="p-5 space-y-5">
        {loading ? (
          <div className="py-8 text-center text-slate-500 animate-pulse text-xs font-medium">
            Loading food traditions for {activeStop?.destination_name}...
          </div>
        ) : (
          <>
            {/* Overview Banner */}
            {food.culinary_heritage && (
              <div className="p-3.5 bg-blue-50/60 border border-blue-200 rounded-xl text-xs text-slate-700 leading-relaxed flex items-start gap-2.5">
                <Sparkles className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-blue-900 mr-1">Culinary Heritage:</span>
                  {food.culinary_heritage}
                </div>
              </div>
            )}

            {/* Signature Dishes Grid */}
            <div>
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Flame className="w-3.5 h-3.5 text-blue-600" />
                Signature Dishes & Specialties ({activeStop?.destination_name})
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {signatureDishes.map((dish: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3.5 bg-white border border-slate-200 rounded-xl hover:border-blue-300 transition-all shadow-sm"
                  >
                    <div className="flex justify-between items-start">
                      <span className="font-bold text-sm text-slate-900">
                        {dish.name}
                      </span>
                      {dish.spice_level && (
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                          {dish.spice_level}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 mt-1 line-clamp-2">{dish.description}</p>
                    {dish.best_place && (
                      <p className="text-[11px] text-blue-700 mt-2 font-semibold flex items-center gap-1">
                        <MapPin className="w-3 h-3 text-blue-600" /> Best at: {dish.best_place}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Recommended Dining Spots */}
            {diningSpots.length > 0 && (
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <Star className="w-3.5 h-3.5 text-blue-600" />
                  Recommended Authentic Spots
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {diningSpots.map((spot: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex justify-between items-center"
                    >
                      <div>
                        <span className="font-bold text-xs text-slate-900">{spot.name}</span>
                        <p className="text-[11px] text-slate-500 mt-0.5">{spot.specialty || spot.cuisine}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-amber-600 font-bold flex items-center gap-0.5">
                          ★ {spot.rating || '4.6'}
                        </span>
                        <span className="text-[10px] text-slate-500 block font-mono">{spot.price_level || '$$'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};
