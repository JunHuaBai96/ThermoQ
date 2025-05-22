import React, { useState } from 'react';
import { Box, Paper, Typography, Grid, Tooltip } from '@mui/material';
import { styled } from '@mui/material/styles';

const ElementBox = styled(Paper)(({ theme, selected }) => ({
  padding: theme.spacing(1),
  textAlign: 'center',
  cursor: 'pointer',
  transition: 'all 0.2s',
  backgroundColor: selected ? theme.palette.primary.main : theme.palette.background.paper,
  color: selected ? theme.palette.primary.contrastText : theme.palette.text.primary,
  '&:hover': {
    transform: 'scale(1.1)',
    zIndex: 1,
  },
}));

const periodicTableData = [
  { symbol: 'H', name: 'Hydrogen', number: 1, category: 'nonmetal' },
  { symbol: 'He', name: 'Helium', number: 2, category: 'noble gas' },
  { symbol: 'Li', name: 'Lithium', number: 3, category: 'alkali metal' },
  { symbol: 'Be', name: 'Beryllium', number: 4, category: 'alkaline earth metal' },
  { symbol: 'B', name: 'Boron', number: 5, category: 'metalloid' },
  { symbol: 'C', name: 'Carbon', number: 6, category: 'nonmetal' },
  { symbol: 'N', name: 'Nitrogen', number: 7, category: 'nonmetal' },
  { symbol: 'O', name: 'Oxygen', number: 8, category: 'nonmetal' },
  { symbol: 'F', name: 'Fluorine', number: 9, category: 'halogen' },
  { symbol: 'Ne', name: 'Neon', number: 10, category: 'noble gas' },
  // Add more elements as needed
];

const PeriodicTable = ({ onElementSelect }) => {
  const [selectedElement, setSelectedElement] = useState(null);

  const handleElementClick = (element) => {
    setSelectedElement(element);
    onElementSelect(element);
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Periodic Table
      </Typography>
      <Grid container spacing={1} sx={{ maxWidth: 800 }}>
        {periodicTableData.map((element) => (
          <Grid item xs={1} key={element.number}>
            <Tooltip title={`${element.name} (${element.number})`}>
              <ElementBox
                selected={selectedElement?.number === element.number}
                onClick={() => handleElementClick(element)}
                elevation={2}
              >
                <Typography variant="caption" display="block">
                  {element.number}
                </Typography>
                <Typography variant="h6">
                  {element.symbol}
                </Typography>
              </ElementBox>
            </Tooltip>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default PeriodicTable; 