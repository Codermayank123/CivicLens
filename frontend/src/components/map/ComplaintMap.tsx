import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Complaint } from '../../types';
import { StatusBadge, PriorityBadge } from '../ui/Badge';
import { Link } from 'react-router-dom';

function createStatusIcon(status: string) {
  let color = '#4f46e5'; // default indigo
  if (status === 'resolved' || status === 'closed') color = '#10b981'; // emerald
  else if (status === 'in_progress') color = '#06b6d4'; // cyan
  else if (status === 'submitted') color = '#f59e0b'; // amber
  else if (status === 'reopened') color = '#e11d48'; // rose

  return L.divIcon({
    className: 'custom-map-marker',
    html: `<div style="background-color: ${color}; width: 24px; height: 24px; border-radius: 50%; border: 2.5px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.25); display: flex; align-items: center; justify-content: center;">
      <div style="background-color: white; width: 6px; height: 6px; border-radius: 50%;"></div>
    </div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 24],
  });
}

interface ComplaintMapProps {
  complaints: Complaint[];
  height?: string;
  center?: [number, number];
  zoom?: number;
}

export const ComplaintMap: React.FC<ComplaintMapProps> = ({
  complaints,
  height = '450px',
  center = [28.6139, 77.209],
  zoom = 13,
}) => {
  const validComplaints = complaints.filter(
    (c) => typeof c.latitude === 'number' && typeof c.longitude === 'number'
  );

  const initialCenter = validComplaints.length > 0
    ? [validComplaints[0].latitude!, validComplaints[0].longitude!] as [number, number]
    : center;

  return (
    <div
      style={{ height }}
      className="w-full rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 shadow-sm z-0"
    >
      <MapContainer center={initialCenter} zoom={zoom} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {validComplaints.map((c) => (
          <Marker
            key={c.id}
            position={[c.latitude!, c.longitude!]}
            icon={createStatusIcon(c.status)}
          >
            <Popup>
              <div className="p-1 space-y-2 min-w-[200px]">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs font-bold text-slate-500">#{c.public_id}</span>
                  <StatusBadge status={c.status} />
                </div>
                <h4 className="font-semibold text-sm text-slate-900 leading-tight">{c.title}</h4>
                <p className="text-xs text-slate-600 line-clamp-2">{c.description}</p>
                {c.address && (
                  <p className="text-[11px] text-slate-500 italic">{c.address}</p>
                )}
                <div className="pt-2 border-t border-slate-100 flex justify-between items-center">
                  <PriorityBadge priority={c.priority} />
                  <Link
                    to={`/complaints/${c.id}`}
                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
                  >
                    View Details →
                  </Link>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};
