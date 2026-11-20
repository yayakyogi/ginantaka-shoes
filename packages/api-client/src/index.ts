import createClient from 'openapi-fetch';

import type { components, paths } from './schema';

export type { components, paths };

/** Typed client for the Ginantaka Shoes API (ADR 0005). */
export function createApiClient(baseUrl: string) {
	return createClient<paths>({ baseUrl });
}

export type ApiClient = ReturnType<typeof createApiClient>;
