import React from 'react';
import { FiPlus, FiX } from 'react-icons/fi';
import './FloatingActionButton.css';

const FloatingActionButton = ({ onClick, isOpen }) => {
    return (
        <button
            className={`floating-action-button ${isOpen ? 'open' : ''}`}
            onClick={onClick}
            aria-label={isOpen ? "Close compose" : "Compose new"}
        >
            {isOpen ? <FiX size={28} /> : <FiPlus size={28} />}
        </button>
    );
};

export default FloatingActionButton;
