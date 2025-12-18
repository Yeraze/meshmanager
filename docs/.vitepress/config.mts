import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "MeshManager",
  description: "Management and oversight application for MeshMonitor and Meshtastic MQTT",
  base: '/',  // Custom domain: meshmanager.org

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/images/logo.svg' }],
    ['meta', { name: 'theme-color', content: '#3eaf7c' }],
    ['meta', { name: 'og:type', content: 'website' }],
    ['meta', { name: 'og:site_name', content: 'MeshManager' }],
  ],

  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    logo: '/images/logo.svg',

    nav: [
      { text: 'Home', link: '/' },
      { text: 'Getting Started', link: '/getting-started' },
      { text: 'Features', link: '/features/' },
      { text: 'Configuration', link: '/configuration/' },
      { text: 'API', link: '/api/' },
    ],

    sidebar: {
      '/features/': [
        {
          text: 'Features',
          items: [
            { text: 'Overview', link: '/features/' },
            { text: 'Dashboard', link: '/features/dashboard' },
            { text: 'Node Details', link: '/features/node-details' },
            { text: 'Solar Monitoring', link: '/features/solar-monitoring' },
            { text: 'Notifications', link: '/features/notifications' },
            { text: 'Multi-Source Support', link: '/features/multi-source' },
          ]
        }
      ],
      '/configuration/': [
        {
          text: 'Configuration',
          items: [
            { text: 'Overview', link: '/configuration/' },
            { text: 'Docker Deployment', link: '/configuration/docker' },
            { text: 'Environment Variables', link: '/configuration/environment' },
            { text: 'Data Sources', link: '/configuration/sources' },
            { text: 'Solar Integration', link: '/configuration/solar' },
            { text: 'Notifications', link: '/configuration/notifications' },
          ]
        }
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Overview', link: '/api/' },
            { text: 'Nodes', link: '/api/nodes' },
            { text: 'Telemetry', link: '/api/telemetry' },
            { text: 'Sources', link: '/api/sources' },
            { text: 'Analysis', link: '/api/analysis' },
          ]
        }
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/yeraze/meshmanager' }
    ],

    footer: {
      message: 'Released under the <a href="https://github.com/yeraze/meshmanager/blob/main/LICENSE" target="_blank">BSD-3-Clause License</a>.',
      copyright: 'Copyright © 2024-present MeshManager Contributors'
    },

    search: {
      provider: 'local'
    },

    editLink: {
      pattern: 'https://github.com/yeraze/meshmanager/edit/main/docs/:path',
      text: 'Edit this page on GitHub'
    }
  },

  // Enable last updated timestamp
  lastUpdated: true,

  // Markdown configuration
  markdown: {
    lineNumbers: true
  },

  // Ignore dead links during build (TODO: create all pages and remove this)
  ignoreDeadLinks: true
})
