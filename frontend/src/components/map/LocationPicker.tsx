import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Navigation } from 'lucide-react';
import { Button } from '../ui/Button';

// Fix Leaflet marker icon asset paths for Vite bundlers
const customIcon = L.divIcon({
  className: 'custom-leaflet-marker',
  html: `<div style="background-color: #4f46e5; width: 28px; height: 28px; border-radius: 50%; border: 3px solid white; box-shadow: 0 4px 6px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white;">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
  </div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
});

interface LocationPickerProps {
  latitude?: number;
  longitude?: number;
  onChange: (lat: number, lng: number) => void;
  onGetCurrentLocation?: () => void;
  isLocating?: boolean;
}

const MapClickHandler: React.FC<{ onLocationSelect: (lat: number, lng: number) => void }> = ({
  onLocationSelect,
}) => {
  useMapEvents({
    click(e) {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

const MapViewportUpdater: React.FC<{ latitude: number; longitude: number }> = ({
  latitude,
  longitude,
}) => {
  const map = useMap();

  useEffect(() => {
    map.setView([latitude, longitude], Math.max(map.getZoom(), 14));
  }, [latitude, longitude, map]);

  return null;
};

export const LocationPicker: React.FC<LocationPickerProps> = ({
  latitude = 28.6139,
  longitude = 77.209,
  onChange,
  onGetCurrentLocation,
  isLocating = false,
}) => {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1">
          <MapPin className="w-3.5 h-3.5 text-indigo-500" /> Click anywhere on map to position pin
        </span>
        {onGetCurrentLocation && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onGetCurrentLocation}
            isLoading={isLocating}
            leftIcon={<Navigation className="w-3 h-3 text-indigo-500" />}
            className="text-xs py-1 px-2.5 h-7"
          >
            Locate Me
          </Button>
        )}
      </div>

      <div className="h-56 w-full rounded-xl overflow-hidden border border-slate-300 dark:border-slate-700 shadow-inner z-0">
        <MapContainer
          center={[latitude, longitude]}
          zoom={14}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapViewportUpdater latitude={latitude} longitude={longitude} />
          <Marker position={[latitude, longitude]} icon={customIcon} />
          <MapClickHandler onLocationSelect={onChange} />
        </MapContainer>
      </div>

      <div className="text-[11px] text-slate-500 font-mono flex gap-4">
        <span>Lat: {latitude.toFixed(5)}</span>
        <span>Lng: {longitude.toFixed(5)}</span>
      </div>
    </div>
  );
};
