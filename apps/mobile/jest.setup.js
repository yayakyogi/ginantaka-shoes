// Reanimated 4 / Worklets need native modules that do not exist under Jest.
// Both packages ship official mocks; use them in every test.
jest.mock('react-native-worklets', () => require('react-native-worklets/src/mock'));
jest.mock('react-native-reanimated', () => require('react-native-reanimated/mock'));
