import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Page from './+page.svelte';

// Phase 0 scaffold smoke test (no AC ID). Replaced by real tests in Phase 4.
describe('root page', () => {
	it('renders', () => {
		render(Page);
		expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
	});
});
