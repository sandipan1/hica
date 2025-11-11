// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	integrations: [
		starlight({
			title: 'HICA Documentation',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/sandipan1/hica' }],
			sidebar: [
				{
					label: 'Overview',
					items: [
						{ label: 'Welcome', link: '/' },
						{ label: 'Getting Started', link: '/getting-started/' },
						{ label: 'Quickstart', link: '/quickstart/' },
					],
				},
				{
					label: 'Core Concepts',
					items: [
						{ label: 'Architecture', link: '/architecture/' },
						{ label: 'Threads & Events', link: '/threads-events/' },
						{ label: 'Tools', link: '/tools/' },
						{ label: 'MCP Integration', link: '/mcp/' },
					],
				},
				{
					label: 'Guides',
					items: [
						{ label: 'Configuration', link: '/configuration/' },
						{ label: 'Logging', link: '/logging/' },
						{ label: 'Deployment (Vercel)', link: '/deploy/' },
					],
				},
			],
		}),
	],
});
