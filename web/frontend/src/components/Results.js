import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';

const Results = () => {
  const navigate = useNavigate();

  // TODO: Replace with actual results data
  const results = {
    compositions: [
      { element: 'Iron', symbol: 'Fe', percentage: 70, unit: 'wt%' },
      { element: 'Carbon', symbol: 'C', percentage: 30, unit: 'wt%' },
    ],
    calculations: {
      qSigmaBin: 0.85,
      qTrue: 0.92,
      qMult: 0.88,
    },
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Calculation Results
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Input Compositions
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Element</TableCell>
                <TableCell>Symbol</TableCell>
                <TableCell>Percentage</TableCell>
                <TableCell>Unit</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {results.compositions.map((comp, index) => (
                <TableRow key={index}>
                  <TableCell>{comp.element}</TableCell>
                  <TableCell>{comp.symbol}</TableCell>
                  <TableCell>{comp.percentage}</TableCell>
                  <TableCell>{comp.unit}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Calculation Results
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Method</TableCell>
                <TableCell>Value</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>QΣbin</TableCell>
                <TableCell>{results.calculations.qSigmaBin}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Qtrue</TableCell>
                <TableCell>{results.calculations.qTrue}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Qmult</TableCell>
                <TableCell>{results.calculations.qMult}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => navigate('/')}
        >
          New Calculation
        </Button>
      </Box>
    </Box>
  );
};

export default Results; 