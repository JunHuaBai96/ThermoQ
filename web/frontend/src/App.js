import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Calculator from './components/Calculator';
import Results from './components/Results';
import PeriodicTable from './components/PeriodicTable';
import CompositionInput from './components/CompositionInput';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  const [selectedElement, setSelectedElement] = useState(null);
  const [composition, setComposition] = useState([]);

  const handleElementSelect = (element) => {
    setSelectedElement(element);
  };

  const handleCompositionChange = (newComposition) => {
    setComposition(newComposition);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ flexGrow: 1 }}>
          <AppBar position="static">
            <Toolbar>
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                ThermoQ Web
              </Typography>
            </Toolbar>
          </AppBar>
          <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Routes>
              <Route path="/" element={
                <Box sx={{ my: 4 }}>
                  <Typography variant="h3" component="h1" gutterBottom align="center">
                    ThermoQ Web
                  </Typography>
                  <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
                    <PeriodicTable onElementSelect={handleElementSelect} />
                  </Paper>
                  <Paper elevation={3} sx={{ p: 3 }}>
                    <CompositionInput
                      onCompositionChange={handleCompositionChange}
                      selectedElement={selectedElement}
                    />
                  </Paper>
                </Box>
              } />
              <Route path="/results" element={<Results />} />
            </Routes>
          </Container>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App; 