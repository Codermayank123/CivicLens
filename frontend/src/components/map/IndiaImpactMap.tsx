import React from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { StateMetric } from '../../types';

// Geographic centroids are static map metadata; all counts and percentages
// come from the database-backed /public/india or /analytics/india endpoint.
const STATE_CENTROIDS: Array<[string, [number, number]]> = [
  ['Andhra Pradesh', [15.9, 79.7]], ['Arunachal Pradesh', [28.2, 94.7]], ['Assam', [26.2, 92.9]], ['Bihar', [25.9, 85.3]],
  ['Chhattisgarh', [21.3, 81.9]], ['Goa', [15.3, 74.1]], ['Gujarat', [22.3, 71.6]], ['Haryana', [29.1, 76.1]],
  ['Himachal Pradesh', [31.1, 77.2]], ['Jharkhand', [23.6, 85.3]], ['Karnataka', [15.3, 75.7]], ['Kerala', [10.5, 76.3]],
  ['Madhya Pradesh', [23.5, 78.5]], ['Maharashtra', [19.7, 75.7]], ['Manipur', [24.7, 93.9]], ['Meghalaya', [25.5, 91.4]],
  ['Mizoram', [23.2, 92.9]], ['Nagaland', [26.1, 94.6]], ['Odisha', [20.3, 85.8]], ['Punjab', [31.1, 75.3]],
  ['Rajasthan', [27.0, 74.2]], ['Sikkim', [27.5, 88.5]], ['Tamil Nadu', [11.0, 78.0]], ['Telangana', [17.9, 79.2]],
  ['Tripura', [23.8, 91.3]], ['Uttar Pradesh', [26.8, 80.9]], ['Uttarakhand', [30.1, 79.1]], ['West Bengal', [23.0, 87.8]],
  ['Andaman and Nicobar Islands', [11.7, 92.7]], ['Chandigarh', [30.7, 76.8]], ['Dadra and Nagar Haveli and Daman and Diu', [20.2, 73.0]],
  ['Delhi', [28.6, 77.2]], ['Jammu and Kashmir', [33.8, 76.6]], ['Ladakh', [34.2, 77.6]], ['Lakshadweep', [10.6, 72.6]], ['Puducherry', [11.9, 79.8]],
];

export const INDIA_STATES = STATE_CENTROIDS.map(([state]) => state);

export const IndiaImpactMap: React.FC<{ metrics: StateMetric[]; onSelect?: (state: string) => void }> = ({ metrics, onSelect }) => {
  const byState = new Map(metrics.map((metric) => [metric.state.toLowerCase(), metric]));
  return (
    <div className="overflow-hidden rounded-2xl border border-[#dcc6a7]">
      <MapContainer center={[22.5, 79]} zoom={4.5} minZoom={4} maxZoom={8} scrollWheelZoom={false} className="h-[440px] w-full">
        <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {STATE_CENTROIDS.map(([state, center]) => {
          const metric = byState.get(state.toLowerCase());
          const count = metric?.total_complaints || 0;
          const color = count === 0 ? '#8b7780' : (metric?.resolution_percentage || 0) >= 75 ? '#286b50' : '#e87924';
          return (
            <CircleMarker key={state} center={center} radius={Math.min(18, 6 + Math.sqrt(count))} pathOptions={{ color, fillColor: color, fillOpacity: 0.65 }} eventHandlers={{ click: () => onSelect?.(state) }}>
              <Popup><strong>{state}</strong><br />Complaints: {count}<br />Resolved: {metric?.resolved_complaints || 0}<br />Resolution: {metric?.resolution_percentage || 0}%</Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
};
