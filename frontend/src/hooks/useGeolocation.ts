import { useState, useCallback } from 'react';
import { locationService, AddressDetails } from '../services/location.service';

export function useGeolocation() {
  const [coordinates, setCoordinates] = useState<{ lat: number; lng: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [address, setAddress] = useState<AddressDetails | null>(null);

  const getCurrentLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const nextCoordinates = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        };
        setCoordinates(nextCoordinates);
        try {
          setAddress(await locationService.reverseGeocode(nextCoordinates.lat, nextCoordinates.lng));
        } catch {
          setAddress(null);
          setError('Location found, but the address could not be resolved. You can enter it manually.');
        }
        setLoading(false);
      },
      (err) => {
        const messages: Record<number, string> = {
          1: 'Location permission was denied. Allow location access or place the pin manually.',
          2: 'Your location is unavailable. Try again or place the pin manually.',
          3: 'Location lookup timed out. Try again or place the pin manually.',
        };
        setError(messages[err.code] || err.message || 'Unable to retrieve location');
        setLoading(false);
      },
      { timeout: 15000, enableHighAccuracy: true, maximumAge: 30000 }
    );
  }, []);

  return {
    coordinates,
    setCoordinates,
    loading,
    error,
    address,
    getCurrentLocation,
  };
}
