/**
 * Tanya Russian Trainer - Client API Module
 * Communicates with server.py endpoints with graceful fallbacks
 */

const API = {
  baseUrl: window.location.origin,

  async getState(day = null) {
    try {
      const url = day ? `${this.baseUrl}/api/state?day=${encodeURIComponent(day)}` : `${this.baseUrl}/api/state`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.warn('API getState fallback:', e);
      return null;
    }
  },

  async getLesson(sessionId) {
    try {
      const res = await fetch(`${this.baseUrl}/api/lesson?id=${encodeURIComponent(sessionId)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.warn('API getLesson error:', e);
      return null;
    }
  },

  async searchVocabulary(query, base = '') {
    try {
      const url = base 
        ? `${this.baseUrl}/api/vocabulary?q=${encodeURIComponent(query)}&base=${encodeURIComponent(base)}`
        : `${this.baseUrl}/api/vocabulary?q=${encodeURIComponent(query)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.warn('API searchVocabulary error:', e);
      return [];
    }
  },

  async getTaxonomy() {
    try {
      const res = await fetch(`${this.baseUrl}/api/taxonomy`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.warn('API getTaxonomy error:', e);
      return null;
    }
  },

  async postProgress(data) {
    try {
      const res = await fetch(`${this.baseUrl}/api/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.warn('API postProgress error:', e);
      return null;
    }
  },

  async logBehavior(data) {
    try {
      await fetch(`${this.baseUrl}/api/behavior`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    } catch (e) {
      // Non-critical logging
    }
  },

  async getBookmarks() {
    try {
      const res = await fetch(`${this.baseUrl}/api/bookmarks`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.warn('API getBookmarks error:', e);
      return { bookmarks: [] };
    }
  },

  async toggleBookmark(data) {
    try {
      const res = await fetch(`${this.baseUrl}/api/bookmarks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.warn('API toggleBookmark error:', e);
      return null;
    }
  },

  async reviewBookmark(data) {
    try {
      const res = await fetch(`${this.baseUrl}/api/bookmarks/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.warn('API reviewBookmark error:', e);
      return null;
    }
  }
};

window.API = API;
