import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatPanel } from '../ChatPanel';

const mockSendMessage = vi.fn();

vi.mock('../../../hooks/useAgents', () => ({
  useChat: vi.fn(() => ({
    messages: [],
    sendMessage: mockSendMessage,
    isLoading: false,
    error: null,
  })),
}));

// Need to import after mock setup
import { useChat } from '../../../hooks/useAgents';
const mockUseChat = vi.mocked(useChat);

describe('ChatPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // jsdom doesn't implement scrollIntoView
    Element.prototype.scrollIntoView = vi.fn();
    mockUseChat.mockReturnValue({
      messages: [],
      sendMessage: mockSendMessage,
      isLoading: false,
      error: null,
    });
  });

  it('renders suggested prompts when no messages', () => {
    render(<ChatPanel />);
    expect(screen.getByText('What are the top risks?')).toBeInTheDocument();
    expect(screen.getByText('Simulate Suez Canal closure')).toBeInTheDocument();
    expect(screen.getByText('Why was order PO-2025-0042 rerouted?')).toBeInTheDocument();
  });

  it('renders input field', () => {
    render(<ChatPanel />);
    expect(screen.getByPlaceholderText('Ask the supply chain AI...')).toBeInTheDocument();
  });

  it('allows typing a message', async () => {
    const user = userEvent.setup();
    render(<ChatPanel />);
    const input = screen.getByPlaceholderText('Ask the supply chain AI...');
    await user.type(input, 'Hello world');
    expect(input).toHaveValue('Hello world');
  });

  it('shows messages when present', () => {
    mockUseChat.mockReturnValue({
      messages: [
        { role: 'user', content: 'What are the risks?', timestamp: '2025-01-01T00:00:00Z' },
        { role: 'assistant', content: 'Here are the top risks...', timestamp: '2025-01-01T00:00:01Z' },
      ],
      sendMessage: mockSendMessage,
      isLoading: false,
      error: null,
    });

    render(<ChatPanel />);
    expect(screen.getByText('What are the risks?')).toBeInTheDocument();
    expect(screen.getByText('Here are the top risks...')).toBeInTheDocument();
  });

  it('calls sendMessage when Send button is clicked', async () => {
    const user = userEvent.setup();
    render(<ChatPanel />);
    const input = screen.getByPlaceholderText('Ask the supply chain AI...');
    await user.type(input, 'Test message');
    await user.click(screen.getByText('Send'));
    expect(mockSendMessage).toHaveBeenCalledWith('Test message');
  });
});
