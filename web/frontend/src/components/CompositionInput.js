import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';

const CompositionInput = ({ onCompositionChange }) => {
  const [selectedElement, setSelectedElement] = useState(null);
  const [composition, setComposition] = useState([]);
  const [amount, setAmount] = useState('');

  const handleAddElement = () => {
    if (selectedElement && amount && !isNaN(amount) && parseFloat(amount) > 0) {
      const newComposition = [
        ...composition,
        {
          element: selectedElement,
          amount: parseFloat(amount),
        },
      ];
      setComposition(newComposition);
      onCompositionChange(newComposition);
      setAmount('');
    }
  };

  const handleRemoveElement = (index) => {
    const newComposition = composition.filter((_, i) => i !== index);
    setComposition(newComposition);
    onCompositionChange(newComposition);
  };

  const handleElementSelect = (element) => {
    setSelectedElement(element);
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        System Composition
      </Typography>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
          <TextField
            label="Amount"
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            sx={{ width: '150px' }}
          />
          <Button
            variant="contained"
            onClick={handleAddElement}
            disabled={!selectedElement || !amount}
          >
            Add Element
          </Button>
        </Box>
        <List>
          {composition.map((item, index) => (
            <ListItem key={index}>
              <ListItemText
                primary={`${item.element.symbol} (${item.element.name})`}
                secondary={`Amount: ${item.amount}`}
              />
              <ListItemSecondaryAction>
                <IconButton
                  edge="end"
                  aria-label="delete"
                  onClick={() => handleRemoveElement(index)}
                >
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      </Paper>
    </Box>
  );
};

export default CompositionInput; 