import React, { useState, useEffect } from 'react';
import { Palette, Scissors, Sparkles, Music, ShoppingBag, Compass } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../common/Card';
import { Button } from '../common/Button';
import { getDestinationCulture } from '../../api/destinations';

interface CultureDiscoveryCardProps {
  stops: any[];
  onOpenCultureModal: (destId: string) => void;
}

export const CultureDiscoveryCard: React.FC<CultureDiscoveryCardProps> = ({ stops, onOpenCultureModal }) => {
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

  const textiles = cultureData?.textiles_and_crafts?.textiles || [];
  const crafts = cultureData?.textiles_and_crafts?.crafts || [];
  const performingArts = cultureData?.performing_arts || {};
  const markets = cultureData?.markets_and_shopping || [];

  return (
    <Card className="bg-white border-slate-200 shadow-sm">
      <CardHeader className="p-5 border-b border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-50/50">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <Palette className="w-5 h-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-slate-900">
              Heritage, Textiles & Performing Arts
            </CardTitle>
            <p className="text-xs text-slate-500">
              Handlooms, artisan crafts, traditional music & vibrant markets
            </p>
          </div>
        </div>

        {/* Destination Tabs */}
        <div className="flex items-center gap-2">
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

          <Button
            onClick={() => onOpenCultureModal(activeStop.destination_id || activeStop.destination_name)}
            variant="secondary"
            className="text-xs py-1.5 px-3 border-blue-200 text-blue-700 hover:bg-blue-50 flex items-center gap-1"
          >
            <Compass className="w-3.5 h-3.5" /> Full Guide
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-5 space-y-5">
        {loading ? (
          <div className="py-8 text-center text-slate-500 animate-pulse text-xs font-medium">
            Loading cultural traditions for {activeStop?.destination_name}...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Column 1: Textiles & Handlooms */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
              <h4 className="text-xs font-bold text-blue-700 uppercase tracking-wider flex items-center gap-1.5">
                <Scissors className="w-4 h-4 text-blue-600" />
                Textiles & Weaving
              </h4>
              {textiles.length === 0 ? (
                <p className="text-xs text-slate-500">Regional handloom weaving traditions.</p>
              ) : (
                textiles.slice(0, 2).map((item: any, idx: number) => (
                  <div key={idx} className="space-y-1">
                    <span className="text-xs font-bold text-slate-900 block">{item.name}</span>
                    <p className="text-[11px] text-slate-600 leading-relaxed">{item.description}</p>
                    {item.famous_hubs && (
                      <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 inline-block mt-1">
                        Hub: {item.famous_hubs[0]}
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Column 2: Artisan Crafts */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
              <h4 className="text-xs font-bold text-blue-700 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-blue-600" />
                Artisan Crafts & Art
              </h4>
              {crafts.length === 0 ? (
                <p className="text-xs text-slate-500">Master artisan heritage.</p>
              ) : (
                crafts.slice(0, 2).map((item: any, idx: number) => (
                  <div key={idx} className="space-y-1">
                    <span className="text-xs font-bold text-slate-900 block">{item.name}</span>
                    <p className="text-[11px] text-slate-600 leading-relaxed">{item.description}</p>
                  </div>
                ))
              )}
            </div>

            {/* Column 3: Music, Dance & Markets */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
              <h4 className="text-xs font-bold text-blue-700 uppercase tracking-wider flex items-center gap-1.5">
                <Music className="w-4 h-4 text-blue-600" />
                Performing Arts & Bazaars
              </h4>
              {performingArts.dance && (
                <div className="text-xs">
                  <span className="text-blue-900 font-bold">Dance/Music: </span>
                  <span className="text-slate-800">{performingArts.dance}</span>
                  {performingArts.music && <span className="text-slate-500"> ({performingArts.music})</span>}
                </div>
              )}
              {markets.length > 0 && (
                <div className="pt-2 border-t border-slate-200 space-y-1">
                  <span className="text-[11px] font-bold text-slate-500 flex items-center gap-1">
                    <ShoppingBag className="w-3 h-3 text-blue-600" /> Best Markets:
                  </span>
                  {markets.slice(0, 2).map((m: any, idx: number) => (
                    <div key={idx} className="text-xs text-slate-800 flex justify-between">
                      <span className="font-semibold">{m.name}</span>
                      <span className="text-slate-500 text-[10px]">{m.known_for}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
