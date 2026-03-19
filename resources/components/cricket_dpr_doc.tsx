import React, { useState } from 'react';
import { FileText, ChevronDown, ChevronRight } from 'lucide-react';

const DPRDocument = () => {
  const [expandedSections, setExpandedSections] = useState({});

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const sections = [
    {
      id: 'executive',
      title: '1. Executive Summary',
      content: (
        <div className="space-y-4">
          <p className="text-gray-700 leading-relaxed">
            The Cricket Analytics Platform is an intelligent, AI-powered data analytics application designed to provide cricket enthusiasts, particularly betting fans, with highly accurate match outcome predictions and real-time insights. By aggregating data from multiple free APIs and employing advanced machine learning algorithms, the platform delivers comprehensive statistical analysis to help users make informed decisions.
          </p>
          <div className="bg-blue-50 p-4 rounded-lg">
            <h4 className="font-semibold text-blue-900 mb-2">Project Vision</h4>
            <p className="text-blue-800 text-sm">
              To become the most reliable and comprehensive cricket prediction platform that democratizes access to professional-grade analytics for every cricket fan.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="bg-green-50 p-3 rounded">
              <h5 className="font-semibold text-green-900 text-sm">Target Market</h5>
              <p className="text-green-800 text-xs mt-1">Cricket betting enthusiasts, fantasy league players, casual fans</p>
            </div>
            <div className="bg-purple-50 p-3 rounded">
              <h5 className="font-semibold text-purple-900 text-sm">Unique Value</h5>
              <p className="text-purple-800 text-xs mt-1">AI-driven predictions with 85%+ accuracy using ensemble models</p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'introduction',
      title: '2. Introduction',
      content: (
        <div className="space-y-4">
          <h4 className="font-semibold text-gray-800">2.1 Project Background</h4>
          <p className="text-gray-700 leading-relaxed">
            This project emerged from a personal curiosity to understand the intricate patterns and statistical relationships that determine cricket match outcomes. With the exponential growth of cricket betting markets (valued at $10+ billion globally) and fantasy cricket platforms, there exists a significant demand for reliable, data-driven prediction tools.
          </p>
          
          <h4 className="font-semibold text-gray-800 mt-6">2.2 Problem Statement</h4>
          <p className="text-gray-700 leading-relaxed">
            Current cricket prediction platforms suffer from several limitations:
          </p>
          <ul className="list-disc ml-6 text-gray-700 space-y-2">
            <li><strong>Incomplete Data Sources:</strong> Reliance on single API endpoints leading to data gaps</li>
            <li><strong>Static Analysis:</strong> Lack of real-time updates during live matches</li>
            <li><strong>Poor Accuracy:</strong> Simple statistical models without machine learning</li>
            <li><strong>Limited Context:</strong> Ignoring crucial factors like pitch conditions, weather, player form</li>
            <li><strong>No Fallback Mechanisms:</strong> Complete failure when primary data sources are unavailable</li>
          </ul>

          <h4 className="font-semibold text-gray-800 mt-6">2.3 Project Objectives</h4>
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-lg">
            <ul className="space-y-3 text-gray-800">
              <li className="flex items-start">
                <span className="font-bold text-indigo-600 mr-2">Primary:</span>
                <span>Develop an AI-powered platform with 85%+ prediction accuracy for match outcomes</span>
              </li>
              <li className="flex items-start">
                <span className="font-bold text-indigo-600 mr-2">Secondary:</span>
                <span>Implement multi-source data aggregation with automatic fallback mechanisms</span>
              </li>
              <li className="flex items-start">
                <span className="font-bold text-indigo-600 mr-2">Tertiary:</span>
                <span>Create scalable architecture for future expansion to other sports</span>
              </li>
            </ul>
          </div>

          <h4 className="font-semibold text-gray-800 mt-6">2.4 Target Audience</h4>
          <div className="grid grid-cols-3 gap-3 mt-3">
            <div className="bg-orange-50 p-3 rounded-lg">
              <h5 className="font-semibold text-orange-900 text-sm mb-2">Betting Enthusiasts</h5>
              <p className="text-xs text-orange-800">Users seeking numerical accuracy and probability-based insights for informed betting decisions</p>
            </div>
            <div className="bg-teal-50 p-3 rounded-lg">
              <h5 className="font-semibold text-teal-900 text-sm mb-2">Fantasy League Players</h5>
              <p className="text-xs text-teal-800">Participants in Dream11, FanCode, and other fantasy platforms needing player performance predictions</p>
            </div>
            <div className="bg-pink-50 p-3 rounded-lg">
              <h5 className="font-semibold text-pink-900 text-sm mb-2">Cricket Analysts</h5>
              <p className="text-xs text-pink-800">Enthusiasts and semi-professionals looking for deep statistical insights and trends</p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'tech-stack',
      title: '3. Technology Stack',
      content: (
        <div className="space-y-4">
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white border border-gray-300">
              <thead className="bg-gray-800 text-white">
                <tr>
                  <th className="px-4 py-3 text-left">Layer</th>
                  <th className="px-4 py-3 text-left">Technology</th>
                  <th className="px-4 py-3 text-left">Purpose</th>
                  <th className="px-4 py-3 text-left">Version</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold bg-blue-50">Frontend</td>
                  <td className="px-4 py-3">Angular</td>
                  <td className="px-4 py-3">SPA framework for responsive UI</td>
                  <td className="px-4 py-3">17.x</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold bg-blue-50">Backend</td>
                  <td className="px-4 py-3">Django + Django REST Framework</td>
                  <td className="px-4 py-3">RESTful API development, ORM</td>
                  <td className="px-4 py-3">5.0+</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold bg-blue-50">Database</td>
                  <td className="px-4 py-3">PostgreSQL</td>
                  <td className="px-4 py-3">Relational data storage, JSONB support</td>
                  <td className="px-4 py-3">16.x</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold bg-blue-50">Containerization</td>
                  <td className="px-4 py-3">Docker + Docker Compose</td>
                  <td className="px-4 py-3">Environment consistency, deployment</td>
                  <td className="px-4 py-3">24.x</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold bg-green-50" rowSpan="4">AI/ML Stack</td>
                  <td className="px-4 py-3">scikit-learn</td>
                  <td className="px-4 py-3">Traditional ML algorithms</td>
                  <td className="px-4 py-3">1.3+</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3">TensorFlow / PyTorch</td>
                  <td className="px-4 py-3">Deep learning models</td>
                  <td className="px-4 py-3">2.15+ / 2.1+</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3">Hugging Face Transformers</td>
                  <td className="px-4 py-3">LLM integration for text analysis</td>
                  <td className="px-4 py-3">4.36+</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3">Pandas, NumPy</td>
                  <td className="px-4 py-3">Data manipulation and analysis</td>
                  <td className="px-4 py-3">2.x / 1.26+</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold bg-purple-50" rowSpan="2">Web Scraping</td>
                  <td className="px-4 py-3">BeautifulSoup4</td>
                  <td className="px-4 py-3">HTML parsing</td>
                  <td className="px-4 py-3">4.12+</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3">Selenium</td>
                  <td className="px-4 py-3">Dynamic content scraping</td>
                  <td className="px-4 py-3">4.16+</td>
                </tr>
                <tr className="border-b">
                  <td className="px-4 py-3 font-semibold bg-yellow-50">Task Queue</td>
                  <td className="px-4 py-3">Celery + Redis</td>
                  <td className="px-4 py-3">Asynchronous task processing</td>
                  <td className="px-4 py-3">5.3+ / 7.x</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 font-semibold bg-red-50">Monitoring</td>
                  <td className="px-4 py-3">Prometheus + Grafana</td>
                  <td className="px-4 py-3">System metrics and visualization</td>
                  <td className="px-4 py-3">Latest</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h4 className="font-semibold text-gray-800 mt-6">3.1 Architecture Justification</h4>
          <div className="bg-gray-50 p-4 rounded-lg space-y-3 text-sm">
            <p><strong className="text-gray-800">Angular Frontend:</strong> <span className="text-gray-700">Chosen for its robust TypeScript support, component-based architecture, and excellent tooling for large-scale applications. Built-in RxJS enables efficient handling of real-time data streams.</span></p>
            
            <p><strong className="text-gray-800">Django Backend:</strong> <span className="text-gray-700">Python ecosystem integration is crucial for ML/AI libraries. Django's ORM simplifies database operations, while Django REST Framework accelerates API development with automatic serialization and authentication.</span></p>
            
            <p><strong className="text-gray-800">PostgreSQL:</strong> <span className="text-gray-700">Superior JSONB support for flexible schema storage, advanced indexing for fast queries, and excellent integration with Django ORM. Handles complex analytical queries efficiently.</span></p>
            
            <p><strong className="text-gray-800">Docker:</strong> <span className="text-gray-700">Ensures development-production parity, simplifies dependency management, and enables horizontal scaling through container orchestration.</span></p>
          </div>
        </div>
      )
    },
    {
      id: 'workflow',
      title: '4. Application Workflow',
      content: (
        <div className="space-y-6">
          <h4 className="font-semibold text-gray-800">4.1 System Architecture Overview</h4>
          <div className="bg-gradient-to-br from-gray-50 to-gray-100 p-6 rounded-lg border-2 border-gray-300">
            <div className="text-xs font-mono space-y-1 text-gray-700">
              <div>┌─────────────────────────────────────────────────┐</div>
              <div>│           USER INTERFACE (Angular)              │</div>
              <div>│  Dashboard | Predictions | Analytics | Profile  │</div>
              <div>└────────────────┬────────────────────────────────┘</div>
              <div>                 │ REST API (HTTPS)</div>
              <div>┌────────────────▼────────────────────────────────┐</div>
              <div>│        DJANGO BACKEND (API Layer)               │</div>
              <div>│  Auth | Matches | Predictions | Analytics       │</div>
              <div>└──────┬─────────────────┬────────────────────────┘</div>
              <div>       │                 │</div>
              <div>       │                 │</div>
              <div>┌──────▼────────┐  ┌─────▼──────────────────────┐</div>
              <div>│ Data Sources  │  │   AI/ML Processing         │</div>
              <div>│ APIs+Scraping │  │   Feature Engineering      │</div>
              <div>└───────┬───────┘  │   ML Model Ensemble        │</div>
              <div>        │          │   LLM Integration          │</div>
              <div>        │          └────────────────────────────┘</div>
              <div>        │</div>
              <div>┌───────▼──────────────────────────────────────┐</div>
              <div>│  PostgreSQL Database + Redis Cache           │</div>
              <div>└──────────────────────────────────────────────┘</div>
            </div>
          </div>

          <h4 className="font-semibold text-gray-800 mt-6">4.2 Detailed Workflow Steps</h4>
          
          <div className="space-y-4">
            <div className="border-l-4 border-blue-500 pl-4 py-2 bg-blue-50">
              <h5 className="font-semibold text-blue-900">Step 1: User Request</h5>
              <p className="text-sm text-blue-800 mt-1">User navigates to match prediction page. Angular frontend sends authenticated API request to Django backend with match ID and prediction parameters.</p>
            </div>

            <div className="border-l-4 border-green-500 pl-4 py-2 bg-green-50">
              <h5 className="font-semibold text-green-900">Step 2: Data Aggregation</h5>
              <p className="text-sm text-green-800 mt-1">Backend initiates parallel data fetching from multiple sources:</p>
              <ul className="text-sm text-green-800 mt-2 ml-4 list-disc">
                <li><strong>Primary:</strong> Free APIs (TheSportsDB, CricketData.org, GitHub Cricket API)</li>
                <li><strong>Secondary:</strong> Web scraping (Cricinfo, Cricbuzz, ICC) if APIs fail</li>
                <li><strong>Caching:</strong> Check Redis for recent data to reduce external calls</li>
              </ul>
            </div>

            <div className="border-l-4 border-purple-500 pl-4 py-2 bg-purple-50">
              <h5 className="font-semibold text-purple-900">Step 3: Data Cleaning and Validation</h5>
              <p className="text-sm text-purple-800 mt-1">Raw data undergoes comprehensive cleaning:</p>
              <ul className="text-sm text-purple-800 mt-2 ml-4 list-disc">
                <li>Remove duplicates and null values</li>
                <li>Standardize player names, team names, venue spellings</li>
                <li>Handle missing data using statistical imputation</li>
                <li>Validate data integrity with consistency checks</li>
                <li>LLM-assisted cleaning for ambiguous text fields</li>
              </ul>
            </div>

            <div className="border-l-4 border-orange-500 pl-4 py-2 bg-orange-50">
              <h5 className="font-semibold text-orange-900">Step 4: Feature Engineering</h5>
              <p className="text-sm text-orange-800 mt-1">Transform cleaned data into ML-ready features:</p>
              <ul className="text-sm text-orange-800 mt-2 ml-4 list-disc">
                <li><strong>Team Features:</strong> Win rate last 10 matches, head-to-head record, home/away performance</li>
                <li><strong>Player Features:</strong> Recent form (last 5 innings), strike rate, average, consistency score</li>
                <li><strong>Environmental:</strong> Pitch type encoding, weather conditions, venue history</li>
                <li><strong>Contextual:</strong> Tournament stage, match importance, team momentum</li>
              </ul>
            </div>

            <div className="border-l-4 border-red-500 pl-4 py-2 bg-red-50">
              <h5 className="font-semibold text-red-900">Step 5: AI Model Prediction</h5>
              <p className="text-sm text-red-800 mt-1">Ensemble model generates predictions:</p>
              <ul className="text-sm text-red-800 mt-2 ml-4 list-disc">
                <li><strong>Random Forest:</strong> Captures non-linear relationships (Weight: 30%)</li>
                <li><strong>XGBoost:</strong> Handles imbalanced data excellently (Weight: 35%)</li>
                <li><strong>Neural Network:</strong> Deep pattern recognition (Weight: 25%)</li>
                <li><strong>Meta Learner:</strong> Combines predictions optimally (Weight: 10%)</li>
                <li><strong>Output:</strong> Win probability, confidence interval, key influencing factors</li>
              </ul>
            </div>

            <div className="border-l-4 border-teal-500 pl-4 py-2 bg-teal-50">
              <h5 className="font-semibold text-teal-900">Step 6: Result Visualization</h5>
              <p className="text-sm text-teal-800 mt-1">Angular frontend receives prediction and displays:</p>
              <ul className="text-sm text-teal-800 mt-2 ml-4 list-disc">
                <li>Win probability gauge with confidence bands</li>
                <li>Historical performance charts</li>
                <li>Key player impact scores</li>
                <li>Real-time odds comparison (if available)</li>
                <li>Exportable PDF report with detailed analytics</li>
              </ul>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'conclusion',
      title: '5. Conclusion',
      content: (
        <div className="space-y-6">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 rounded-lg">
            <h4 className="font-bold text-xl mb-3">Project Summary</h4>
            <p className="text-sm leading-relaxed opacity-90">
              The Cricket Analytics Platform represents a comprehensive solution that combines cutting-edge AI/ML technologies with robust data engineering to deliver unprecedented accuracy in cricket match predictions. By addressing the critical pain points of existing platforms—data reliability, prediction accuracy, and real-time updates—this application is positioned to become the go-to tool for cricket betting enthusiasts and fantasy league players worldwide.
            </p>
          </div>

          <h4 className="font-semibold text-gray-800">Key Success Metrics (Year 1)</h4>
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-green-100 p-3 rounded text-center">
              <p className="text-2xl font-bold text-green-900">86%+</p>
              <p className="text-xs text-green-700">Prediction Accuracy</p>
            </div>
            <div className="bg-blue-100 p-3 rounded text-center">
              <p className="text-2xl font-bold text-blue-900">5,000+</p>
              <p className="text-xs text-blue-700">Active Users</p>
            </div>
            <div className="bg-purple-100 p-3 rounded text-center">
              <p className="text-2xl font-bold text-purple-900">99.5%</p>
              <p className="text-xs text-purple-700">System Uptime</p>
            </div>
            <div className="bg-orange-100 p-3 rounded text-center">
              <p className="text-2xl font-bold text-orange-900">6+</p>
              <p className="text-xs text-orange-700">Data Sources</p>
            </div>
          </div>

          <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-6 rounded-lg mt-6">
            <h4 className="font-bold text-lg mb-3">Final Thoughts</h4>
            <p className="text-sm leading-relaxed opacity-90 mb-4">
              This Cricket Analytics Platform is more than just a prediction tool—it's an educational resource that empowers users to understand the complex dynamics of cricket through data-driven insights. By maintaining ethical standards, respecting intellectual property, and prioritizing user privacy, the platform aims to build trust and long-term user loyalty in the competitive sports analytics market.
            </p>
            <p className="text-sm leading-relaxed opacity-90">
              The robust technical foundation (Angular + Django + PostgreSQL + Docker) combined with state-of-the-art machine learning ensures scalability and adaptability as the platform evolves. With a clear monetization strategy and realistic growth projections, this project has the potential to transform from a personal curiosity into a sustainable, profitable business serving cricket fans globally.
            </p>
          </div>
        </div>
      )
    }
  ];

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white rounded-lg shadow-2xl p-8 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold mb-2">Cricket Analytics Platform</h1>
              <p className="text-lg opacity-90">Detailed Project Report (DPR)</p>
              <p className="text-sm opacity-75 mt-2">AI-Powered Match Prediction and Analytics System</p>
            </div>
            <FileText size={64} className="opacity-50" />
          </div>
          <div className="mt-6 grid grid-cols-4 gap-4 text-center">
            <div className="bg-white bg-opacity-20 rounded p-3">
              <p className="text-2xl font-bold">26</p>
              <p className="text-xs">Weeks Timeline</p>
            </div>
            <div className="bg-white bg-opacity-20 rounded p-3">
              <p className="text-2xl font-bold">86%</p>
              <p className="text-xs">Target Accuracy</p>
            </div>
            <div className="bg-white bg-opacity-20 rounded p-3">
              <p className="text-2xl font-bold">6+</p>
              <p className="text-xs">Data Sources</p>
            </div>
            <div className="bg-white bg-opacity-20 rounded p-3">
              <p className="text-2xl font-bold">$68</p>
              <p className="text-xs">Monthly Cost</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-4 flex items-center">
            <FileText size={24} className="mr-2 text-blue-600" />
            Table of Contents
          </h2>
          <div className="grid grid-cols-2 gap-2">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => toggleSection(section.id)}
                className="text-left px-4 py-2 rounded hover:bg-blue-50 transition-colors flex items-center justify-between"
              >
                <span className="text-sm text-gray-700">{section.title}</span>
                {expandedSections[section.id] ? (
                  <ChevronDown size={16} className="text-blue-600" />
                ) : (
                  <ChevronRight size={16} className="text-gray-400" />
                )}
              </button>
            ))}
          </div>
        </div>

        {sections.map((section) => (
          <div key={section.id} className="mb-6">
            <div className="bg-white rounded-lg shadow-lg overflow-hidden">
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full px-6 py-4 bg-gradient-to-r from-gray-50 to-gray-100 hover:from-gray-100 hover:to-gray-200 transition-all flex items-center justify-between"
              >
                <h3 className="text-xl font-bold text-gray-800">{section.title}</h3>
                {expandedSections[section.id] ? (
                  <ChevronDown size={24} className="text-blue-600" />
                ) : (
                  <ChevronRight size={24} className="text-gray-400" />
                )}
              </button>
              {expandedSections[section.id] && (
                <div className="p-6 border-t border-gray-200">
                  {section.content}
                </div>
              )}
            </div>
          </div>
        ))}

        <div className="bg-gray-800 text-white rounded-lg p-6 text-center">
          <p className="text-sm opacity-75">
            Document Generated: December 2025 | Version 1.0
          </p>
          <p className="text-xs opacity-50 mt-2">
            For questions or collaboration opportunities, contact: developer@cricketanalytics.com
          </p>
        </div>
      </div>
    </div>
  );
};

export default DPRDocument;