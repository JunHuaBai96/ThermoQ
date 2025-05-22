import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import axios from 'axios';

const Calculator = () => {
  const [elements, setElements] = useState([]);
  const [selectedElement, setSelectedElement] = useState('');
  const [percentage, setPercentage] = useState('');
  const [unit, setUnit] = useState('wt%');
  const [compositions, setCompositions] = useState([]);

  useEffect(() => {
    // Fetch elements from backend
    const fetchElements = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/elements');
        setElements(response.data);
      } catch (error) {
        console.error('Error fetching elements:', error);
      }
    };
    fetchElements();
  }, []);

  const handleAddElement = () => {
    if (selectedElement && percentage) {
      const newComposition = {
        element: elements.find(e => e.id === selectedElement),
        percentage: parseFloat(percentage),
        unit,
      };
      setCompositions([...compositions, newComposition]);
      setSelectedElement('');
      setPercentage('');
    }
  };

  const handleRemoveElement = (index) => {
    const newCompositions = compositions.filter((_, i) => i !== index);
    setCompositions(newCompositions);
  };

  const handleCalculate = async () => {
    try {
      const response = await axios.post('http://localhost:5000/api/calculate', {
        compositions,
      });
      // Handle calculation results
      console.log(response.data);
    } catch (error) {
      console.error('Error calculating:', error);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Element Composition Calculator
      </Typography>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={4}>
            <FormControl fullWidth>
              <InputLabel>Element</InputLabel>
              <Select
                value={selectedElement}
                onChange={(e) => setSelectedElement(e.target.value)}
                label="Element"
              >
                {elements.map((element) => (
                  <MenuItem key={element.id} value={element.id}>
                    {element.symbol} - {element.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={3}>
            <TextField
              fullWidth
              label="Percentage"
              type="number"
              value={percentage}
              onChange={(e) => setPercentage(e.target.value)}
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <FormControl fullWidth>
              <InputLabel>Unit</InputLabel>
              <Select
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                label="Unit"
              >
                <MenuItem value="wt%">Weight %</MenuItem>
                <MenuItem value="at%">Atomic %</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={2}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleAddElement}
              disabled={!selectedElement || !percentage}
            >
              Add
            </Button>
          </Grid>
        </Grid>
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Element</TableCell>
              <TableCell>Symbol</TableCell>
              <TableCell>Percentage</TableCell>
              <TableCell>Unit</TableCell>
              <TableCell>Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {compositions.map((comp, index) => (
              <TableRow key={index}>
                <TableCell>{comp.element.name}</TableCell>
                <TableCell>{comp.element.symbol}</TableCell>
                <TableCell>{comp.percentage}</TableCell>
                <TableCell>{comp.unit}</TableCell>
                <TableCell>
                  <Button
                    color="error"
                    onClick={() => handleRemoveElement(index)}
                  >
                    Remove
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleCalculate}
          disabled={compositions.length === 0}
        >
          Calculate
        </Button>
      </Box>
    </Box>
  );
};

export default Calculator; 