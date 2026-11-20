import { render, screen } from '@testing-library/react-native';

import HomeScreen from '@/app/index';

// Phase 0 scaffold smoke test (no AC ID). Replaced by real tests in Phase 5.
describe('<HomeScreen />', () => {
  test('renders the default screen', async () => {
    await render(<HomeScreen />);
    expect(screen.getByText('get started')).toBeTruthy();
  });
});
