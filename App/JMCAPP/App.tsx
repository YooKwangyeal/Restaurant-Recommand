/**
 * JMC 맛집 추천 앱 - WebView 기반
 * FastAPI 백엔드와 연동된 웹뷰 앱
 *
 * @format
 */

import React from 'react';
import {
  StatusBar,
  StyleSheet,
  useColorScheme,
  View,
  BackHandler,
  Alert,
} from 'react-native';
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';

// FastAPI 서버 URL (개발용)
const WEB_URL = 'http://localhost:8000';
// 실제 배포시에는 실제 서버 URL로 변경
// const WEB_URL = 'https://your-fastapi-server.com';

function App() {
  const isDarkMode = useColorScheme() === 'dark';

  return (
    <SafeAreaProvider>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
      <AppContent />
    </SafeAreaProvider>
  );
}

function AppContent() {
  const safeAreaInsets = useSafeAreaInsets();
  const webViewRef = React.useRef<WebView>(null);

  // 안드로이드 뒤로가기 버튼 처리
  React.useEffect(() => {
    const onBackPress = () => {
      if (webViewRef.current) {
        webViewRef.current.goBack();
        return true; // 기본 뒤로가기 동작 방지
      }
      return false;
    };

    const backHandler = BackHandler.addEventListener(
      'hardwareBackPress',
      onBackPress,
    );
    return () => backHandler.remove();
  }, []);

  const handleError = (error: any) => {
    console.error('WebView Error:', error);
    Alert.alert(
      '연결 오류',
      'FastAPI 서버에 연결할 수 없습니다.\n서버가 실행 중인지 확인해주세요.',
      [{ text: '확인' }],
    );
  };

  const handleLoadStart = () => {
    console.log('WebView loading started');
  };

  const handleLoadEnd = () => {
    console.log('WebView loading finished');
  };

  return (
    <View style={[styles.container, { paddingTop: safeAreaInsets.top }]}>
      <WebView
        ref={webViewRef}
        source={{ uri: WEB_URL }}
        style={styles.webview}
        onError={handleError}
        onHttpError={handleError}
        onLoadStart={handleLoadStart}
        onLoadEnd={handleLoadEnd}
        startInLoadingState={true}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        allowsBackForwardNavigationGestures={true}
        // iOS에서 줌 비활성화
        scalesPageToFit={false}
        // 안전한 브라우징을 위한 설정
        mixedContentMode="compatibility"
        allowsInlineMediaPlayback={true}
        mediaPlaybackRequiresUserAction={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#667eea',
  },
  webview: {
    flex: 1,
  },
});

export default App;
