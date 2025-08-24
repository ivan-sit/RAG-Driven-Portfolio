import React, { useState, useEffect } from 'react';
import { registerRootComponent } from 'expo';
import {
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  RefreshControl,
  Alert,
  Linking,
} from 'react-native';
import { Card, Title, Paragraph, Button, ActivityIndicator } from 'react-native-paper';

// Configuration - will be loaded from API
const DEFAULT_CONFIG = {
  api_base_url: 'http://localhost:8000',
  refresh_interval: 300, // 5 minutes in seconds
  max_retries: 3,
  timeout: 30,
};

const App = () => {
  const [summaries, setSummaries] = useState(null);
  const [investmentIdeas, setInvestmentIdeas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [apiBaseUrl, setApiBaseUrl] = useState(DEFAULT_CONFIG.api_base_url);

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/config`);
      const configData = await response.json();
      
      // Update API base URL if provided in config
      if (configData.api?.server?.host && configData.api?.server?.port) {
        const newApiUrl = `http://${configData.api.server.host}:${configData.api.server.port}`;
        setApiBaseUrl(newApiUrl);
      }
      
      // Update mobile config
      const mobileConfig = {
        ...DEFAULT_CONFIG,
        refresh_interval: configData.app?.mobile?.refresh_interval || DEFAULT_CONFIG.refresh_interval,
        max_retries: configData.app?.mobile?.max_retries || DEFAULT_CONFIG.max_retries,
        timeout: configData.app?.mobile?.timeout || DEFAULT_CONFIG.timeout,
      };
      setConfig(mobileConfig);
      
    } catch (error) {
      console.error('Error fetching config:', error);
      // Use default config if API is not available
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch summaries
      const summariesResponse = await fetch(`${apiBaseUrl}/fetchSummaries`);
      const summariesData = await summariesResponse.json();
      
      // Fetch investment ideas
      const ideasResponse = await fetch(`${apiBaseUrl}/fetchInvestmentIdeas`);
      const ideasData = await ideasResponse.json();
      
      setSummaries(summariesData);
      setInvestmentIdeas(ideasData);
      setLastUpdate(new Date().toLocaleTimeString());
      
    } catch (error) {
      console.error('Error fetching data:', error);
      Alert.alert('Error', 'Failed to fetch data from server');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  useEffect(() => {
    const initializeApp = async () => {
      // First fetch configuration
      await fetchConfig();
      
      // Then fetch initial data
      await fetchData();
    };
    
    initializeApp();
    
    // Set up polling based on config
    const interval = setInterval(fetchData, config.refresh_interval * 1000);
    
    return () => clearInterval(interval);
  }, [config.refresh_interval, apiBaseUrl]);

  const openUrl = (url) => {
    Linking.openURL(url).catch(err => {
      Alert.alert('Error', 'Could not open link');
    });
  };

  const renderSourceReferences = (sources) => {
    if (!sources || sources.length === 0) return null;
    
    return (
      <View style={styles.sourcesContainer}>
        <Text style={styles.sourcesTitle}>Sources:</Text>
        {sources.map((source, index) => (
          <TouchableOpacity
            key={index}
            onPress={() => openUrl(source.url)}
            style={styles.sourceItem}
          >
            <Text style={styles.sourceText}>
              {source.source} - {new Date(source.timestamp).toLocaleDateString()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    );
  };

  const renderIndustrySummary = (summary, title, icon) => (
    <Card style={styles.card}>
      <Card.Content>
        <View style={styles.headerRow}>
          <Text style={styles.icon}>{icon}</Text>
          <Title style={styles.title}>{title}</Title>
        </View>
        <Paragraph style={styles.summaryText}>
          {summary.summary_text}
        </Paragraph>
        {renderSourceReferences(summary.sources)}
        <Text style={styles.timestamp}>
          Generated: {new Date(summary.generated_at).toLocaleString()}
        </Text>
      </Card.Content>
    </Card>
  );

  const renderInvestmentIdeas = () => {
    if (!investmentIdeas) return null;

    return (
      <Card style={styles.card}>
        <Card.Content>
          <Title style={styles.title}>📈 Investment Ideas</Title>
          
          {/* Long-term stocks */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Long-term Stock Picks</Text>
            {investmentIdeas.long_term_stocks.map((stock, index) => (
              <View key={index} style={styles.stockItem}>
                <View style={styles.stockHeader}>
                  <Text style={styles.ticker}>{stock.ticker}</Text>
                  <Text style={styles.companyName}>{stock.company_name}</Text>
                </View>
                <Text style={styles.reason}>{stock.reason}</Text>
                {renderSourceReferences(stock.source_references)}
              </View>
            ))}
          </View>

          {/* Short-term options */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Short-term Option Plays</Text>
            {investmentIdeas.short_term_options.map((option, index) => (
              <View key={index} style={styles.optionItem}>
                <View style={styles.optionHeader}>
                  <Text style={styles.ticker}>{option.ticker}</Text>
                  <Text style={[
                    styles.optionType,
                    { color: option.option_type === 'call' ? '#4CAF50' : '#F44336' }
                  ]}>
                    {option.option_type.toUpperCase()}
                  </Text>
                  <Text style={styles.strikePrice}>${option.strike_price}</Text>
                </View>
                <Text style={styles.optionDetails}>
                  Expires: {option.expiration_date} | Direction: {option.direction}
                </Text>
                <Text style={styles.reason}>{option.reason}</Text>
                {renderSourceReferences(option.source_references)}
              </View>
            ))}
          </View>

          <Text style={styles.timestamp}>
            Generated: {new Date(investmentIdeas.generated_at).toLocaleString()}
          </Text>
        </Card.Content>
      </Card>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#2196F3" />
          <Text style={styles.loadingText}>Loading investment insights...</Text>
          <Text style={styles.loadingSubtext}>Connecting to {apiBaseUrl}</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#f5f5f5" />
      
      <View style={styles.header}>
        <Text style={styles.headerTitle}>RAG-Driven Portfolio</Text>
        <Text style={styles.headerSubtitle}>AI-Powered Investment Insights</Text>
        {lastUpdate && (
          <Text style={styles.lastUpdate}>Last updated: {lastUpdate}</Text>
        )}
        <Text style={styles.apiUrl}>API: {apiBaseUrl}</Text>
      </View>

      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {summaries && (
          <>
            {renderIndustrySummary(
              summaries.defense_summary,
              'Defense Industry Summary',
              '🛡️'
            )}
            
            {renderIndustrySummary(
              summaries.semiconductor_summary,
              'Semiconductor Industry Summary',
              '💾'
            )}
          </>
        )}

        {renderInvestmentIdeas()}

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Data refreshes automatically every {Math.round(config.refresh_interval / 60)} minutes
          </Text>
          <TouchableOpacity onPress={onRefresh} style={styles.refreshButton}>
            <Text style={styles.refreshButtonText}>Refresh Now</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  loadingSubtext: {
    marginTop: 8,
    fontSize: 12,
    color: '#999',
  },
  header: {
    backgroundColor: '#2196F3',
    padding: 20,
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginBottom: 8,
  },
  lastUpdate: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.7)',
    marginBottom: 4,
  },
  apiUrl: {
    fontSize: 10,
    color: 'rgba(255, 255, 255, 0.6)',
  },
  scrollView: {
    flex: 1,
    padding: 16,
  },
  card: {
    marginBottom: 16,
    elevation: 4,
    borderRadius: 12,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  icon: {
    fontSize: 24,
    marginRight: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  summaryText: {
    fontSize: 14,
    lineHeight: 20,
    color: '#555',
    marginBottom: 12,
  },
  sourcesContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  sourcesTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#666',
    marginBottom: 8,
  },
  sourceItem: {
    marginBottom: 4,
  },
  sourceText: {
    fontSize: 12,
    color: '#2196F3',
    textDecorationLine: 'underline',
  },
  timestamp: {
    fontSize: 11,
    color: '#999',
    marginTop: 8,
    fontStyle: 'italic',
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  stockItem: {
    marginBottom: 16,
    padding: 12,
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
  },
  stockHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  ticker: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2196F3',
    marginRight: 8,
  },
  companyName: {
    fontSize: 14,
    color: '#666',
    flex: 1,
  },
  reason: {
    fontSize: 13,
    lineHeight: 18,
    color: '#555',
  },
  optionItem: {
    marginBottom: 16,
    padding: 12,
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
  },
  optionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  optionType: {
    fontSize: 12,
    fontWeight: 'bold',
    marginRight: 8,
  },
  strikePrice: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
  },
  optionDetails: {
    fontSize: 12,
    color: '#666',
    marginBottom: 8,
  },
  footer: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  footerText: {
    fontSize: 12,
    color: '#999',
    marginBottom: 12,
  },
  refreshButton: {
    backgroundColor: '#2196F3',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
  },
  refreshButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: 'bold',
  },
});

export default App;
