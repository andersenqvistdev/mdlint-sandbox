/**
 * Forge Dashboard - Main JavaScript Client
 *
 * Real-time dashboard for monitoring company operations.
 * Uses SSE (Server-Sent Events) for live updates.
 *
 * @version 0.1.0
 */

(function() {
  'use strict';

  // ============================================================================
  // Configuration
  // ============================================================================

  const CONFIG = {
    SSE_ENDPOINT: '/api/stream',
    API_ENDPOINT: '/api/dashboard',
    RECONNECT_BASE_DELAY: 1000,
    RECONNECT_MAX_DELAY: 30000,
    HEARTBEAT_TIMEOUT: 60000,
    THEME_STORAGE_KEY: 'forge-dashboard-theme',
    STATE_STORAGE_KEY: 'forge-dashboard-state'
  };

  // ============================================================================
  // State Management
  // ============================================================================

  const state = {
    eventSource: null,
    reconnectAttempts: 0,
    reconnectTimeout: null,
    lastHeartbeat: null,
    heartbeatTimer: null,
    cachedData: null,
    isConnected: false,
    currentPanel: 'health'
  };

  // ============================================================================
  // DOM Elements Cache
  // ============================================================================

  const elements = {
    // Connection status
    connectionIndicator: null,
    connectionText: null,
    lastUpdateTime: null,

    // Panels
    panels: null,
    navItems: null,

    // Health panel
    healthScore: null,
    healthProgress: null,
    healthFactors: null,

    // Tasks panel
    tasksPending: null,
    tasksActive: null,
    tasksBlocked: null,
    tasksCompleted: null,
    tasksBadge: null,
    velocityDaily: null,
    velocityWeekly: null,
    velocityTrend: null,

    // Organization panel - Current Work
    currentTask: null,
    currentTaskTitle: null,
    currentTaskDescription: null,
    currentTaskStatus: null,
    currentTaskId: null,
    currentTaskAssignee: null,
    currentTaskStarted: null,
    activityList: null,
    departmentsContainer: null,

    // Roadmap panel
    phaseList: null,

    // Errors panel
    escalationsTable: null,
    errorTimeline: null,
    errorsBadge: null,
    escalationCount: null,

    // Footer
    daemonStatus: null,
    daemonStatusText: null,

    // Buttons
    refreshHealthBtn: null
  };

  // ============================================================================
  // Initialization
  // ============================================================================

  function init() {
    cacheElements();
    loadThemePreference();
    loadCachedState();
    setupEventListeners();
    fetchInitialData();
    connectSSE();
  }

  function cacheElements() {
    // Connection status
    elements.connectionIndicator = document.getElementById('connection-indicator');
    elements.connectionText = document.getElementById('connection-text');
    elements.lastUpdateTime = document.getElementById('last-update-time');

    // Panels
    elements.panels = document.querySelectorAll('.panel');
    elements.navItems = document.querySelectorAll('.nav__item');

    // Health panel
    elements.healthScore = document.getElementById('health-score');
    elements.healthProgress = document.getElementById('health-progress');
    elements.healthFactors = document.getElementById('health-factors');

    // Tasks panel
    elements.tasksPending = document.getElementById('tasks-pending');
    elements.tasksActive = document.getElementById('tasks-active');
    elements.tasksBlocked = document.getElementById('tasks-blocked');
    elements.tasksCompleted = document.getElementById('tasks-completed');
    elements.tasksBadge = document.getElementById('tasks-badge');
    elements.velocityDaily = document.getElementById('velocity-daily');
    elements.velocityWeekly = document.getElementById('velocity-weekly');
    elements.velocityTrend = document.getElementById('velocity-trend');

    // Organization panel - Current Work
    elements.currentTask = document.getElementById('current-task');
    elements.currentTaskTitle = document.getElementById('current-task-title');
    elements.currentTaskDescription = document.getElementById('current-task-description');
    elements.currentTaskStatus = document.getElementById('current-task-status');
    elements.currentTaskId = document.getElementById('current-task-id');
    elements.currentTaskAssignee = document.getElementById('current-task-assignee');
    elements.currentTaskStarted = document.getElementById('current-task-started');
    elements.activityList = document.getElementById('activity-list');
    elements.departmentsContainer = document.getElementById('departments-container');

    // Roadmap panel
    elements.phaseList = document.getElementById('phase-list');

    // Errors panel
    elements.escalationsTable = document.getElementById('escalations-table');
    elements.errorTimeline = document.getElementById('error-timeline');
    elements.errorsBadge = document.getElementById('errors-badge');
    elements.escalationCount = document.getElementById('escalation-count');

    // Footer
    elements.daemonStatus = document.getElementById('daemon-status');
    elements.daemonStatusText = document.getElementById('daemon-status-text');

    // Buttons
    elements.refreshHealthBtn = document.getElementById('refresh-health');
  }

  // ============================================================================
  // Theme Management
  // ============================================================================

  function loadThemePreference() {
    const savedTheme = localStorage.getItem(CONFIG.THEME_STORAGE_KEY);
    if (savedTheme === 'light') {
      document.body.classList.add('theme--light');
    }
  }

  function toggleTheme() {
    const isLight = document.body.classList.toggle('theme--light');
    localStorage.setItem(CONFIG.THEME_STORAGE_KEY, isLight ? 'light' : 'dark');
  }

  // ============================================================================
  // Cached State Management
  // ============================================================================

  function loadCachedState() {
    try {
      const cached = localStorage.getItem(CONFIG.STATE_STORAGE_KEY);
      if (cached) {
        state.cachedData = JSON.parse(cached);
        // Render cached data immediately for instant display
        if (state.cachedData) {
          renderAllPanels(state.cachedData);
        }
      }
    } catch (e) {
      console.warn('Failed to load cached state:', e);
    }
  }

  function saveCachedState(data) {
    try {
      state.cachedData = data;
      localStorage.setItem(CONFIG.STATE_STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
      console.warn('Failed to save cached state:', e);
    }
  }

  // ============================================================================
  // Event Listeners
  // ============================================================================

  function setupEventListeners() {
    // Tab navigation
    elements.navItems.forEach(function(item) {
      item.addEventListener('click', function() {
        navigateToPanel(this.getAttribute('data-panel'));
      });
    });

    // Refresh button
    if (elements.refreshHealthBtn) {
      elements.refreshHealthBtn.addEventListener('click', function() {
        fetchInitialData();
      });
    }

    // Theme toggle (if element exists)
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', toggleTheme);
    }

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
      // Press 'r' to refresh
      if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const activeElement = document.activeElement;
        if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
          fetchInitialData();
        }
      }
    });
  }

  // ============================================================================
  // Tab Navigation
  // ============================================================================

  function navigateToPanel(panelId) {
    state.currentPanel = panelId;

    // Update active nav item
    elements.navItems.forEach(function(nav) {
      nav.classList.remove('nav__item--active');
      if (nav.getAttribute('data-panel') === panelId) {
        nav.classList.add('nav__item--active');
      }
    });

    // Show corresponding panel
    elements.panels.forEach(function(panel) {
      panel.classList.remove('panel--active');
    });

    const targetPanel = document.getElementById(panelId + '-panel');
    if (targetPanel) {
      targetPanel.classList.add('panel--active');
    }
  }

  // ============================================================================
  // SSE Connection Management
  // ============================================================================

  function connectSSE() {
    if (state.eventSource) {
      state.eventSource.close();
    }

    try {
      state.eventSource = new EventSource(CONFIG.SSE_ENDPOINT);

      state.eventSource.onopen = function() {
        state.isConnected = true;
        state.reconnectAttempts = 0;
        updateConnectionStatus('connected');
        startHeartbeatMonitor();
      };

      state.eventSource.onmessage = function(event) {
        handleSSEMessage(event);
      };

      state.eventSource.onerror = function() {
        state.isConnected = false;
        updateConnectionStatus('disconnected');
        scheduleReconnect();
      };

      // Custom event handlers
      state.eventSource.addEventListener('full', function(event) {
        handleFullUpdate(JSON.parse(event.data));
      });

      state.eventSource.addEventListener('update', function(event) {
        handlePartialUpdate(JSON.parse(event.data));
      });

      state.eventSource.addEventListener('heartbeat', function(event) {
        handleHeartbeat(JSON.parse(event.data));
      });

    } catch (e) {
      console.error('Failed to connect to SSE:', e);
      updateConnectionStatus('error');
      scheduleReconnect();
    }
  }

  function scheduleReconnect() {
    if (state.reconnectTimeout) {
      clearTimeout(state.reconnectTimeout);
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, ... up to 30s
    const delay = Math.min(
      CONFIG.RECONNECT_BASE_DELAY * Math.pow(2, state.reconnectAttempts),
      CONFIG.RECONNECT_MAX_DELAY
    );

    updateConnectionStatus('reconnecting', delay);

    state.reconnectTimeout = setTimeout(function() {
      state.reconnectAttempts++;
      connectSSE();
    }, delay);
  }

  function startHeartbeatMonitor() {
    if (state.heartbeatTimer) {
      clearTimeout(state.heartbeatTimer);
    }

    state.lastHeartbeat = Date.now();

    state.heartbeatTimer = setInterval(function() {
      const elapsed = Date.now() - state.lastHeartbeat;
      if (elapsed > CONFIG.HEARTBEAT_TIMEOUT) {
        console.warn('Heartbeat timeout, reconnecting...');
        state.isConnected = false;
        updateConnectionStatus('timeout');
        if (state.eventSource) {
          state.eventSource.close();
        }
        scheduleReconnect();
      }
    }, CONFIG.HEARTBEAT_TIMEOUT / 2);
  }

  // ============================================================================
  // SSE Message Handlers
  // ============================================================================

  function handleSSEMessage(event) {
    try {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'full':
          handleFullUpdate(data.payload);
          break;
        case 'update':
          handlePartialUpdate(data.payload);
          break;
        case 'heartbeat':
          handleHeartbeat(data);
          break;
        default:
          console.warn('Unknown message type:', data.type);
      }
    } catch (e) {
      console.error('Failed to parse SSE message:', e);
    }
  }

  function handleFullUpdate(data) {
    saveCachedState(data);
    renderAllPanels(data);
    updateTimestamp();
  }

  function handlePartialUpdate(data) {
    // Merge partial update with cached data
    if (state.cachedData) {
      Object.assign(state.cachedData, data);
    } else {
      state.cachedData = data;
    }
    saveCachedState(state.cachedData);

    // Only render affected panels
    if (data.health !== undefined) {
      renderHealth(data.health);
    }
    if (data.progress !== undefined) {
      renderProgress(data.progress);
    }
    if (data.workforce !== undefined) {
      renderWorkforce(data.workforce);
    }
    if (data.roadmap !== undefined) {
      renderRoadmap(data.roadmap);
    }
    if (data.errors !== undefined || data.escalations !== undefined) {
      renderErrors(data);
    }

    // Also refresh current work and activity on any update
    fetchCurrentWork();

    updateTimestamp();
  }

  function fetchCurrentWork() {
    // Fetch current and activity endpoints
    Promise.all([
      fetch('/api/current').then(function(r) { return r.ok ? r.json() : null; }),
      fetch('/api/activity').then(function(r) { return r.ok ? r.json() : null; })
    ])
      .then(function(results) {
        var current = results[0];
        var activity = results[1];

        if (current) {
          renderCurrentWork(current);
        }
        if (activity) {
          renderActivityFeed(activity);
        }
      })
      .catch(function(error) {
        console.error('Failed to fetch current work:', error);
      });
  }

  function handleHeartbeat(data) {
    state.lastHeartbeat = Date.now();

    // Update daemon status if provided
    if (data.daemon_status) {
      updateDaemonStatus(data.daemon_status);
    }
  }

  // ============================================================================
  // Connection Status UI
  // ============================================================================

  function updateConnectionStatus(status, reconnectDelay) {
    if (!elements.connectionIndicator || !elements.connectionText) return;

    // Remove all status classes
    elements.connectionIndicator.classList.remove(
      'connection-status__indicator--connected',
      'connection-status__indicator--disconnected',
      'connection-status__indicator--reconnecting',
      'connection-status__indicator--error'
    );

    switch (status) {
      case 'connected':
        elements.connectionIndicator.classList.add('connection-status__indicator--connected');
        elements.connectionText.textContent = 'Connected';
        break;
      case 'disconnected':
        elements.connectionIndicator.classList.add('connection-status__indicator--disconnected');
        elements.connectionText.textContent = 'Disconnected';
        break;
      case 'reconnecting':
        elements.connectionIndicator.classList.add('connection-status__indicator--reconnecting');
        const seconds = Math.round(reconnectDelay / 1000);
        elements.connectionText.textContent = 'Reconnecting in ' + seconds + 's...';
        break;
      case 'timeout':
        elements.connectionIndicator.classList.add('connection-status__indicator--error');
        elements.connectionText.textContent = 'Connection timeout';
        break;
      case 'error':
        elements.connectionIndicator.classList.add('connection-status__indicator--error');
        elements.connectionText.textContent = 'Connection error';
        break;
    }
  }

  function updateTimestamp() {
    if (!elements.lastUpdateTime) return;

    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
    elements.lastUpdateTime.textContent = timeStr;
  }

  function updateDaemonStatus(status) {
    if (!elements.daemonStatus || !elements.daemonStatusText) return;

    elements.daemonStatus.classList.remove(
      'footer__daemon-status--running',
      'footer__daemon-status--stopped',
      'footer__daemon-status--error'
    );

    if (status === 'running') {
      elements.daemonStatus.classList.add('footer__daemon-status--running');
      elements.daemonStatusText.textContent = 'Running';
    } else if (status === 'stopped') {
      elements.daemonStatus.classList.add('footer__daemon-status--stopped');
      elements.daemonStatusText.textContent = 'Stopped';
    } else {
      elements.daemonStatus.classList.add('footer__daemon-status--error');
      elements.daemonStatusText.textContent = status || 'Unknown';
    }
  }

  // ============================================================================
  // Initial Data Fetch
  // ============================================================================

  function fetchInitialData() {
    // Fetch main data and current work data in parallel
    Promise.all([
      fetch(CONFIG.API_ENDPOINT).then(function(r) { return r.ok ? r.json() : null; }),
      fetch('/api/current').then(function(r) { return r.ok ? r.json() : null; }),
      fetch('/api/activity').then(function(r) { return r.ok ? r.json() : null; })
    ])
      .then(function(results) {
        var data = results[0] || {};
        var current = results[1];
        var activity = results[2];

        // Merge current work and activity into workforce data
        if (!data.workforce) {
          data.workforce = {};
        }
        if (current) {
          data.workforce.current = current;
        }
        if (activity) {
          data.workforce.activity = activity;
        }

        handleFullUpdate(data);
      })
      .catch(function(error) {
        console.error('Failed to fetch initial data:', error);
        // If we have cached data, continue using it
        if (!state.cachedData) {
          showErrorMessage('Failed to load dashboard data. Retrying...');
        }
      });
  }

  // ============================================================================
  // Panel Rendering
  // ============================================================================

  function renderAllPanels(data) {
    if (!data) return;

    if (data.health) {
      renderHealth(data.health);
    }
    if (data.progress) {
      renderProgress(data.progress);
    }
    if (data.workforce) {
      renderWorkforce(data.workforce);
    }
    if (data.roadmap) {
      renderRoadmap(data.roadmap);
    }
    if (data.errors || data.escalations) {
      renderErrors(data);
    }
  }

  // ============================================================================
  // Health Panel Rendering
  // ============================================================================

  function renderHealth(data) {
    if (!data) return;

    // Update health score gauge
    if (data.score !== undefined) {
      updateHealthGauge(data.score);
    }

    // Update health factors
    if (data.factors && elements.healthFactors) {
      renderHealthFactors(data.factors);
    }
  }

  function updateHealthGauge(score) {
    if (!elements.healthScore || !elements.healthProgress) return;

    const circumference = 2 * Math.PI * 80;
    const offset = circumference - (score / 100) * circumference;

    elements.healthProgress.style.strokeDasharray = circumference;
    elements.healthProgress.style.strokeDashoffset = offset;

    // Update color based on score
    elements.healthProgress.classList.remove(
      'health-gauge__progress--warning',
      'health-gauge__progress--critical'
    );

    if (score < 60) {
      elements.healthProgress.classList.add('health-gauge__progress--critical');
    } else if (score < 80) {
      elements.healthProgress.classList.add('health-gauge__progress--warning');
    }

    elements.healthScore.textContent = Math.round(score);
  }

  function renderHealthFactors(factors) {
    if (!elements.healthFactors) return;

    let html = '';

    factors.forEach(function(factor) {
      const statusClass = getProgressBarClass(factor.value, factor.inverted);

      html += '<div class="progress-item">' +
        '<div class="progress-item__header">' +
          '<span class="progress-item__label">' + escapeHtml(factor.label) + '</span>' +
          '<span class="progress-item__value">' + factor.value + '%</span>' +
        '</div>' +
        '<div class="progress-bar">' +
          '<div class="progress-bar__fill ' + statusClass + '" style="width: ' + factor.value + '%"></div>' +
        '</div>' +
      '</div>';
    });

    elements.healthFactors.innerHTML = html;
  }

  function getProgressBarClass(value, inverted) {
    // For inverted metrics (like escalation rate), lower is better
    if (inverted) {
      if (value > 30) return 'progress-bar__fill--error';
      if (value > 15) return 'progress-bar__fill--warning';
      return 'progress-bar__fill--success';
    }

    // Normal metrics - higher is better
    if (value >= 80) return 'progress-bar__fill--success';
    if (value >= 60) return 'progress-bar__fill--warning';
    return 'progress-bar__fill--error';
  }

  // ============================================================================
  // Progress Panel Rendering
  // ============================================================================

  function renderProgress(data) {
    if (!data) return;

    // Update task counts
    if (data.pending !== undefined && elements.tasksPending) {
      elements.tasksPending.textContent = data.pending;
    }
    if (data.active !== undefined && elements.tasksActive) {
      elements.tasksActive.textContent = data.active;
    }
    if (data.blocked !== undefined && elements.tasksBlocked) {
      elements.tasksBlocked.textContent = data.blocked;
    }
    if (data.completed !== undefined && elements.tasksCompleted) {
      elements.tasksCompleted.textContent = data.completed;
    }

    // Update tasks badge
    if (elements.tasksBadge) {
      const activeCount = data.active || 0;
      if (activeCount > 0) {
        elements.tasksBadge.textContent = activeCount;
        elements.tasksBadge.style.display = 'inline';
      } else {
        elements.tasksBadge.style.display = 'none';
      }
    }

    // Update velocity metrics
    if (data.velocity) {
      if (data.velocity.daily !== undefined && elements.velocityDaily) {
        elements.velocityDaily.textContent = data.velocity.daily.toFixed(1);
      }
      if (data.velocity.weekly !== undefined && elements.velocityWeekly) {
        elements.velocityWeekly.textContent = data.velocity.weekly;
      }
      if (data.velocity.trend !== undefined && elements.velocityTrend) {
        const trendValue = data.velocity.trend;
        const prefix = trendValue >= 0 ? '+' : '';
        elements.velocityTrend.textContent = prefix + trendValue + '%';
      }
    }
  }

  // ============================================================================
  // Workforce Panel Rendering (with Current Work)
  // ============================================================================

  function renderWorkforce(data) {
    if (!data) return;

    // Update current work (replaces economics)
    if (data.current) {
      renderCurrentWork(data.current);
    }

    // Update activity feed
    if (data.activity) {
      renderActivityFeed(data.activity);
    }

    // Update departments and employees
    if (data.departments && elements.departmentsContainer) {
      renderDepartments(data.departments);
    }
  }

  function renderCurrentWork(current) {
    // Update current task
    if (current.active_task) {
      var task = current.active_task;

      if (elements.currentTaskTitle) {
        elements.currentTaskTitle.textContent = task.title || 'No title';
      }
      if (elements.currentTaskDescription) {
        elements.currentTaskDescription.textContent = task.description || '';
      }
      if (elements.currentTaskStatus) {
        elements.currentTaskStatus.textContent = task.status || 'unknown';
        elements.currentTaskStatus.className = 'badge badge--' + (task.status === 'in_progress' ? 'warning' : 'info');
      }
      if (elements.currentTaskId) {
        elements.currentTaskId.textContent = task.id || '';
      }
      if (elements.currentTaskAssignee) {
        elements.currentTaskAssignee.textContent = task.assignee ? 'Assignee: ' + task.assignee : '';
      }
      if (elements.currentTaskStarted) {
        elements.currentTaskStarted.textContent = task.started_at ? 'Started: ' + formatTime(task.started_at) : '';
      }
      if (elements.currentTask) {
        elements.currentTask.className = 'current-task current-task--' + (task.status || 'pending');
      }
    } else {
      // No active task
      if (elements.currentTaskTitle) {
        elements.currentTaskTitle.textContent = 'No active task';
      }
      if (elements.currentTaskDescription) {
        elements.currentTaskDescription.textContent = 'The daemon is idle or waiting for work.';
      }
      if (elements.currentTaskStatus) {
        elements.currentTaskStatus.textContent = 'idle';
        elements.currentTaskStatus.className = 'badge badge--muted';
      }
    }

    // Update daemon status in footer
    if (current.daemon_status && elements.daemonStatus) {
      var ds = current.daemon_status;
      var state = ds.state || 'unknown';
      elements.daemonStatus.className = 'status-indicator status-indicator--' +
        (state === 'CLOSED' ? 'success' : state === 'OPEN' ? 'error' : 'warning');
      if (elements.daemonStatusText) {
        elements.daemonStatusText.textContent = 'Daemon: ' + state +
          (ds.tasks_this_hour ? ' (' + ds.tasks_this_hour + ' tasks/hr)' : '');
      }
    }
  }

  function renderActivityFeed(activity) {
    if (!elements.activityList || !activity.activities) return;

    var activities = activity.activities;
    if (activities.length === 0) {
      elements.activityList.innerHTML = '<li class="activity-feed__item">' +
        '<span class="activity-feed__time">--:--</span>' +
        '<span class="activity-feed__text">No recent activity</span>' +
        '</li>';
      return;
    }

    var html = '';
    activities.forEach(function(act, index) {
      var typeClass = act.type === 'success' ? 'activity-feed__item--success' :
                      act.type === 'error' ? 'activity-feed__item--error' : '';
      var newClass = index === 0 ? 'activity-feed__item--new' : '';

      html += '<li class="activity-feed__item ' + typeClass + ' ' + newClass + '">' +
        '<span class="activity-feed__time">' + escapeHtml(act.time || '') + '</span>' +
        '<span class="activity-feed__text">' + escapeHtml(act.text || '') + '</span>' +
        '</li>';
    });

    elements.activityList.innerHTML = html;
  }

  function formatTime(isoString) {
    try {
      var date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
      return isoString;
    }
  }

  function renderDepartments(departments) {
    if (!elements.departmentsContainer) return;

    let html = '';

    departments.forEach(function(dept) {
      html += '<div class="department">' +
        '<div class="department__header">' +
          '<h3 class="department__title">' + escapeHtml(dept.name) + '</h3>' +
          '<span class="department__count">' + dept.employees.length + ' members</span>' +
        '</div>' +
        '<div class="grid grid--auto">';

      dept.employees.forEach(function(emp) {
        html += renderEmployeeCard(emp);
      });

      html += '</div></div>';
    });

    elements.departmentsContainer.innerHTML = html;
  }

  function renderEmployeeCard(employee) {
    const initials = getInitials(employee.name);
    const statusClass = 'employee-card__status--' + (employee.status || 'offline');
    const statusText = capitalizeFirst(employee.status || 'offline');

    return '<div class="employee-card">' +
      '<div class="employee-card__avatar">' + initials + '</div>' +
      '<div class="employee-card__info">' +
        '<div class="employee-card__name">' + escapeHtml(employee.name) + '</div>' +
        '<div class="employee-card__role">' + escapeHtml(employee.role) + '</div>' +
      '</div>' +
      '<span class="employee-card__status ' + statusClass + '">' + statusText + '</span>' +
    '</div>';
  }

  // ============================================================================
  // Roadmap Panel Rendering
  // ============================================================================

  function renderRoadmap(data) {
    if (!data || !elements.phaseList) return;

    let html = '';

    data.phases.forEach(function(phase) {
      const statusClass = 'phase-item__status--' + phase.status;
      const progressClass = phase.progress === 100 ? 'progress-bar__fill--success' : '';

      html += '<div class="phase-item">' +
        '<div class="phase-item__header">' +
          '<h3 class="phase-item__title">' + escapeHtml(phase.name) + '</h3>' +
          '<span class="phase-item__status ' + statusClass + '">' + getStatusLabel(phase.status) + '</span>' +
        '</div>' +
        '<div class="phase-item__meta">' +
          '<span>' + phase.task_count + ' tasks</span>' +
          '<span>' + (phase.target_date ? 'Target: ' + phase.target_date : '') + '</span>' +
        '</div>' +
        '<div class="phase-item__progress">' +
          '<div class="progress-item">' +
            '<div class="progress-item__header">' +
              '<span class="progress-item__label">Progress</span>' +
              '<span class="progress-item__value">' + phase.progress + '%</span>' +
            '</div>' +
            '<div class="progress-bar">' +
              '<div class="progress-bar__fill ' + progressClass + '" style="width: ' + phase.progress + '%"></div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>';
    });

    elements.phaseList.innerHTML = html;
  }

  function getStatusLabel(status) {
    switch (status) {
      case 'completed': return 'Completed';
      case 'active': return 'In Progress';
      case 'pending': return 'Pending';
      default: return capitalizeFirst(status);
    }
  }

  // ============================================================================
  // Errors Panel Rendering
  // ============================================================================

  function renderErrors(data) {
    if (!data) return;

    // Render escalations table
    if (data.escalations && elements.escalationsTable) {
      renderEscalationsTable(data.escalations);
    }

    // Render error timeline
    if (data.errors && elements.errorTimeline) {
      renderErrorTimeline(data.errors);
    }

    // Update error badge
    updateErrorBadge(data.escalations);
  }

  function renderEscalationsTable(escalations) {
    const tbody = elements.escalationsTable.querySelector('tbody');
    if (!tbody) return;

    let html = '';

    if (escalations.length === 0) {
      html = '<tr><td colspan="5" class="table__empty">No active escalations</td></tr>';
    } else {
      escalations.forEach(function(esc) {
        const severityClass = getSeverityBadgeClass(esc.severity);

        html += '<tr>' +
          '<td>' + escapeHtml(esc.id) + '</td>' +
          '<td>' + escapeHtml(esc.type) + '</td>' +
          '<td><span class="badge ' + severityClass + '">' + escapeHtml(esc.severity) + '</span></td>' +
          '<td>' + escapeHtml(esc.assigned || '-') + '</td>' +
          '<td>' + formatAge(esc.created_at) + '</td>' +
        '</tr>';
      });
    }

    tbody.innerHTML = html;

    // Update escalation count badge
    if (elements.escalationCount) {
      elements.escalationCount.textContent = escalations.length;
    }
  }

  function renderErrorTimeline(errors) {
    if (!elements.errorTimeline) return;

    let html = '';
    const shouldScroll = errors.length > 0;
    const previousFirstId = elements.errorTimeline.querySelector('.timeline__item')?.getAttribute('data-id');

    errors.forEach(function(error, index) {
      const markerClass = getTimelineMarkerClass(error.level);
      const isNew = index === 0 && error.id !== previousFirstId;

      html += '<div class="timeline__item' + (isNew ? ' timeline__item--new' : '') + '" data-id="' + (error.id || index) + '">' +
        '<div class="timeline__marker ' + markerClass + '"></div>' +
        '<div class="timeline__time">' + formatTime(error.timestamp) + '</div>' +
        '<div class="timeline__content">' +
          '<div class="timeline__title">' + escapeHtml(error.title) + '</div>' +
          '<div class="timeline__description">' + escapeHtml(error.description) + '</div>' +
        '</div>' +
      '</div>';
    });

    elements.errorTimeline.innerHTML = html;

    // Auto-scroll to new errors if panel is active
    if (shouldScroll && state.currentPanel === 'errors') {
      const newItem = elements.errorTimeline.querySelector('.timeline__item--new');
      if (newItem) {
        newItem.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }

  function updateErrorBadge(escalations) {
    if (!elements.errorsBadge) return;

    const count = escalations ? escalations.length : 0;
    if (count > 0) {
      elements.errorsBadge.textContent = count;
      elements.errorsBadge.style.display = 'inline';
    } else {
      elements.errorsBadge.style.display = 'none';
    }
  }

  function getSeverityBadgeClass(severity) {
    switch ((severity || '').toLowerCase()) {
      case 'critical': return 'badge--error';
      case 'high': return 'badge--error';
      case 'medium': return 'badge--warning';
      case 'low': return 'badge--info';
      default: return 'badge--info';
    }
  }

  function getTimelineMarkerClass(level) {
    switch ((level || '').toLowerCase()) {
      case 'error': return 'timeline__marker--error';
      case 'warning': return 'timeline__marker--warning';
      case 'info': return 'timeline__marker--info';
      default: return '';
    }
  }

  // ============================================================================
  // Utility Functions
  // ============================================================================

  function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
  }

  function formatCurrency(value) {
    if (typeof value !== 'number') return '$0';
    return '$' + value.toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
  }

  function formatAge(timestamp) {
    if (!timestamp) return '-';

    const created = new Date(timestamp);
    const now = new Date();
    const diffMs = now - created;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) {
      return diffMins + 'm';
    }

    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    return hours + 'h ' + mins + 'm';
  }

  function formatTime(timestamp) {
    if (!timestamp) return '--:--:--';

    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false });
  }

  function getInitials(name) {
    if (!name) return '??';

    const words = name.split(/[\s-]+/);
    if (words.length >= 2) {
      return (words[0][0] + words[words.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  }

  function showErrorMessage(message) {
    // Simple error display - could be enhanced with a toast system
    console.error(message);
  }

  // ============================================================================
  // Public API (for debugging)
  // ============================================================================

  window.ForgeDashboard = {
    getState: function() { return state; },
    getCachedData: function() { return state.cachedData; },
    reconnect: connectSSE,
    refresh: fetchInitialData,
    toggleTheme: toggleTheme,
    navigateToPanel: navigateToPanel
  };

  // ============================================================================
  // Initialize on DOM Ready
  // ============================================================================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
