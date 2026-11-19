const configuredApiUrl = import.meta.env.VITE_API_URL?.replace(/\/+$/, '');

export const API_V1_URL = configuredApiUrl
	? configuredApiUrl.endsWith('/api/v1')
		? configuredApiUrl
		: `${configuredApiUrl}/api/v1`
	: '/api/v1';
