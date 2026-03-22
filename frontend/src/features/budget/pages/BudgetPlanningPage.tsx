import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export function BudgetPlanningPage() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/controlling/ebitda', { replace: true });
  }, [navigate]);

  return null;
}
