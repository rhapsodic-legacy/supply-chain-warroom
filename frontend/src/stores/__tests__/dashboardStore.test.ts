import { useDashboardStore } from '../dashboardStore';

describe('dashboardStore', () => {
  beforeEach(() => {
    // Reset store state between tests
    useDashboardStore.setState({
      sidebarOpen: true,
      activePanel: 'overview',
      notifications: [],
    });
  });

  it('toggleSidebar flips the sidebarOpen state', () => {
    expect(useDashboardStore.getState().sidebarOpen).toBe(true);
    useDashboardStore.getState().toggleSidebar();
    expect(useDashboardStore.getState().sidebarOpen).toBe(false);
    useDashboardStore.getState().toggleSidebar();
    expect(useDashboardStore.getState().sidebarOpen).toBe(true);
  });

  it('setActivePanel updates the active panel', () => {
    expect(useDashboardStore.getState().activePanel).toBe('overview');
    useDashboardStore.getState().setActivePanel('risks');
    expect(useDashboardStore.getState().activePanel).toBe('risks');
  });

  it('addNotification adds to notifications array', () => {
    const notification = {
      id: 'n1',
      type: 'risk' as const,
      severity: 'critical' as const,
      title: 'New Risk',
      message: 'Critical risk detected',
      timestamp: new Date().toISOString(),
      read: false,
    };

    useDashboardStore.getState().addNotification(notification);
    expect(useDashboardStore.getState().notifications).toHaveLength(1);
    expect(useDashboardStore.getState().notifications[0].id).toBe('n1');
  });

  it('dismissNotification removes by id', () => {
    const notification1 = {
      id: 'n1',
      type: 'risk' as const,
      severity: 'critical' as const,
      title: 'Risk 1',
      message: 'First risk',
      timestamp: new Date().toISOString(),
      read: false,
    };
    const notification2 = {
      id: 'n2',
      type: 'order' as const,
      severity: 'info' as const,
      title: 'Order update',
      message: 'Order shipped',
      timestamp: new Date().toISOString(),
      read: false,
    };

    useDashboardStore.getState().addNotification(notification1);
    useDashboardStore.getState().addNotification(notification2);
    expect(useDashboardStore.getState().notifications).toHaveLength(2);

    useDashboardStore.getState().dismissNotification('n1');
    expect(useDashboardStore.getState().notifications).toHaveLength(1);
    expect(useDashboardStore.getState().notifications[0].id).toBe('n2');
  });
});
