import React from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { PublicHeatmapPoint } from '../../services/public.service';

export const CivicHeatmap: React.FC<{ points: PublicHeatmapPoint[]; height?: string }> = ({ points, height = '480px' }) => {
  const valid = points.filter((point) => Number.isFinite(point.latitude) && Number.isFinite(point.longitude));
  const center: [number, number] = valid.length ? [valid[0].latitude, valid[0].longitude] : [28.6139, 77.209];
  return (
    <div style={{ height }} className="w-full overflow-hidden rounded-2xl border border-[#dcc6a7] shadow-sm">
      <MapContainer center={center} zoom={12} className="h-full w-full">
        <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {valid.map((point) => (
          <CircleMarker
            key={`${point.latitude}-${point.longitude}-${point.category}`}
            center={[point.latitude, point.longitude]}
            radius={Math.min(28, 8 + point.intensity * 5)}
            pathOptions={{ color: point.status === 'open' ? '#e87924' : '#286b50', fillOpacity: 0.45 }}
          >
            <Popup>
              <strong>{point.category}</strong>
              <br />
              {point.complaint_count} related report{point.complaint_count === 1 ? '' : 's'}
              <br />
              Status: {point.status}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
};
