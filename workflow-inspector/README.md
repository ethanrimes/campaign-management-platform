# Workflow Inspector

A Next.js application for visualizing and inspecting campaign execution traces from the Campaign Management Platform's orchestrator agent workflows.

## Features

- **Execution Selector**: Browse and search through all workflow executions with timestamps
- **Timeline View**: Visual representation of workflow steps (Research → Planning → Content Creation)
- **Research Display**: View gathered insights, hashtags, opportunities, and sources
- **Campaign Plan Display**: Inspect generated campaigns and ad sets with budgets and targeting
- **Content Display**: View generated posts with media previews, hashtags, and platform links
- **Real-time Updates**: Subscribe to execution status changes (for running workflows)

## Prerequisites

- Node.js 18+ and npm/yarn
- Access to your Supabase project
- Supabase project URL and anon key

## Setup

### 1. Install Dependencies

```bash
cd workflow-inspector
npm install
```

### 2. Configure Environment Variables

Copy the environment template and add your Supabase credentials:

```bash
cp .env.local.template .env.local
```

Edit `.env.local` with your values:
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

### 3. Database Requirements

This application requires the following Supabase views/tables to be accessible:
- `execution_summary` (view)
- `execution_logs`
- `campaigns`
- `ad_sets`
- `posts`
- `research`
- `media_files`

The `execution_summary` view should already exist based on migration 007.

### 4. Run the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## Usage

### Viewing Executions

1. **Select an Execution**: Use the dropdown at the top to browse executions by timestamp
   - Search by execution ID, workflow type, or timestamp
   - View quick stats (campaigns, posts, research entries)
   - See execution status (completed, failed, running)

2. **Timeline View**: Shows the workflow progress through three stages:
   - Research: Market insights and trend analysis
   - Planning: Campaign and ad set creation
   - Content Creation: Post and media generation

3. **Tabbed Content Views**:
   - **Research Tab**: View insights, hashtags, opportunities, and sources
   - **Planning Tab**: Inspect campaigns with budgets, ad sets, targeting, and creative briefs
   - **Content Tab**: Browse generated posts with media previews and platform links

### Understanding the Data

#### Execution Status
- 🟢 **Completed**: All workflow steps finished successfully
- 🔴 **Failed**: One or more steps encountered errors
- 🔵 **Running**: Workflow is currently executing

#### Research Data
- **Key Findings**: Important insights from research with relevance scores
- **Content Opportunities**: Actionable suggestions for content strategy
- **Recommended Hashtags**: Trending and relevant hashtags
- **Sources**: Links to research sources

#### Campaign Planning
- **Campaigns**: High-level marketing campaigns with objectives and budgets
- **Ad Sets**: Detailed targeting, creative briefs, and content requirements
- **Materials**: Links, hashtags, and brand assets for content creation

#### Generated Content
- **Posts**: Social media posts with captions, hashtags, and media
- **Media Files**: AI-generated images and videos
- **Platform Links**: Direct links to published Facebook/Instagram posts

## Architecture

### Tech Stack
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Database**: Supabase (PostgreSQL)
- **Icons**: Lucide React
- **Date Handling**: date-fns

### Key Components
- `ExecutionSelector`: Dropdown with search and filtering
- `ExecutionTimeline`: Visual workflow progress indicator
- `ResearchDisplay`: Research insights and opportunities viewer
- `PlanDisplay`: Campaign hierarchy viewer with expandable ad sets
- `ContentDisplay`: Post grid with media previews
- `MediaViewer`: Image/video display with fullscreen support

### Data Flow
1. Execution summaries are fetched from the `execution_summary` view
2. When an execution is selected, all related data is fetched in parallel
3. Data is displayed in organized tabs for easy navigation
4. Real-time subscriptions update the UI for running executions

## Development

### Project Structure
```
workflow-inspector/
├── src/
│   ├── app/           # Next.js app router pages
│   ├── components/    # React components
│   ├── lib/          # Utilities and types
│   └── utils/        # Helper functions
├── public/           # Static assets
└── package.json      # Dependencies
```

### Building for Production

```bash
npm run build
npm start
```

### Deployment

This app can be deployed to:
- **Vercel**: Push to GitHub and connect to Vercel
- **Netlify**: Similar GitHub integration
- **Self-hosted**: Build and serve with Node.js

## Troubleshooting

### Common Issues

1. **No executions showing**: 
   - Check Supabase connection in `.env.local`
   - Verify the `execution_summary` view exists
   - Check browser console for errors

2. **Media not loading**:
   - Verify Supabase storage bucket permissions
   - Check if media URLs are accessible

3. **Real-time updates not working**:
   - Ensure Supabase realtime is enabled for tables
   - Check WebSocket connection in browser

## Future Enhancements

- Export execution reports as PDF
- Compare multiple executions side-by-side
- Advanced filtering and search capabilities
- Performance metrics visualization
- Execution cost analysis
- Automated error diagnostics
- Webhook notifications for failures

## License

Part of the Campaign Management Platform - Internal Use Only