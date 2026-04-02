// frontend/src/App.js
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import './App.css';

// API Service
class ApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'https://api.gymcloud.com';
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    if (config.body && typeof config.body !== 'string') {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Members API
  async getMembers(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/members${queryString ? `?${queryString}` : ''}`);
  }

  async getMember(id) {
    return this.request(`/members/${id}`);
  }

  async createMember(memberData) {
    return this.request('/members', {
      method: 'POST',
      body: memberData,
    });
  }

  async updateMember(id, memberData) {
    return this.request(`/members/${id}`, {
      method: 'PUT',
      body: memberData,
    });
  }

  async deleteMember(id) {
    return this.request(`/members/${id}`, {
      method: 'DELETE',
    });
  }

  // Workouts API
  async getWorkouts(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/workouts${queryString ? `?${queryString}` : ''}`);
  }

  async createWorkout(workoutData) {
    return this.request('/workouts', {
      method: 'POST',
      body: workoutData,
    });
  }

  // Subscriptions API
  async getSubscriptions(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/subscriptions${queryString ? `?${queryString}` : ''}`);
  }

  async createSubscription(subscriptionData) {
    return this.request('/subscriptions', {
      method: 'POST',
      body: subscriptionData,
    });
  }
}

const apiService = new ApiService();

// Components
const Header = () => (
  <header className="header">
    <div className="container">
      <div className="nav-brand">
        <h1>💪 GYMCloud</h1>
      </div>
      <nav className="nav-menu">
        <Link to="/dashboard" className="nav-link">Dashboard</Link>
        <Link to="/members" className="nav-link">Membri</Link>
        <Link to="/workouts" className="nav-link">Allenamenti</Link>
        <Link to="/subscriptions" className="nav-link">Abbonamenti</Link>
        <Link to="/equipment" className="nav-link">Attrezzature</Link>
      </nav>
    </div>
  </header>
);

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalMembers: 0,
    activeMembers: 0,
    todayWorkouts: 0,
    monthlyRevenue: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        // Simulate loading dashboard stats
        setTimeout(() => {
          setStats({
            totalMembers: 245,
            activeMembers: 198,
            todayWorkouts: 42,
            monthlyRevenue: 12500,
          });
          setLoading(false);
        }, 1000);
      } catch (error) {
        console.error('Error loading dashboard:', error);
        setLoading(false);
      }
    };

    loadDashboardData();
  }, []);

  if (loading) {
    return <div className="loading">Caricamento dashboard...</div>;
  }

  return (
    <div className="dashboard">
      <div className="container">
        <h2>Dashboard</h2>
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">👥</div>
            <div className="stat-content">
              <h3>{stats.totalMembers}</h3>
              <p>Membri Totali</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <h3>{stats.activeMembers}</h3>
              <p>Membri Attivi</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🏃‍♂️</div>
            <div className="stat-content">
              <h3>{stats.todayWorkouts}</h3>
              <p>Allenamenti Oggi</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">💰</div>
            <div className="stat-content">
              <h3>€{stats.monthlyRevenue.toLocaleString()}</h3>
              <p>Ricavi Mensili</p>
            </div>
          </div>
        </div>

        <div className="dashboard-charts">
          <div className="chart-container">
            <h3>Panoramica Attività</h3>
            <div className="chart-placeholder">
              <p>📊 Grafici delle attività (in arrivo)</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const Members = () => {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phoneNumber: '',
    subscriptionType: 'basic',
    emergencyContact: {
      name: '',
      phone: '',
    },
  });

  useEffect(() => {
    loadMembers();
  }, []);

  const loadMembers = async () => {
    try {
      setLoading(true);
      const data = await apiService.getMembers();
      setMembers(data.members || []);
    } catch (error) {
      console.error('Error loading members:', error);
      // Mock data for demo
      setMembers([
        {
          memberId: '1',
          firstName: 'Marco',
          lastName: 'Rossi',
          email: 'marco.rossi@email.com',
          phoneNumber: '+39 123 456 7890',
          subscriptionType: 'premium',
          status: 'active',
          joinDate: '2024-01-15',
        },
        {
          memberId: '2',
          firstName: 'Giulia',
          lastName: 'Bianchi',
          email: 'giulia.bianchi@email.com',
          phoneNumber: '+39 987 654 3210',
          subscriptionType: 'basic',
          status: 'active',
          joinDate: '2024-02-10',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingMember) {
        await apiService.updateMember(editingMember.memberId, formData);
      } else {
        await apiService.createMember(formData);
      }
      
      resetForm();
      loadMembers();
    } catch (error) {
      console.error('Error saving member:', error);
      alert('Errore nel salvare il membro: ' + error.message);
    }
  };

  const resetForm = () => {
    setFormData({
      firstName: '',
      lastName: '',
      email: '',
      phoneNumber: '',
      subscriptionType: 'basic',
      emergencyContact: { name: '', phone: '' },
    });
    setEditingMember(null);
    setShowForm(false);
  };

  const startEdit = (member) => {
    setFormData({
      firstName: member.firstName,
      lastName: member.lastName,
      email: member.email,
      phoneNumber: member.phoneNumber,
      subscriptionType: member.subscriptionType,
      emergencyContact: member.emergencyContact || { name: '', phone: '' },
    });
    setEditingMember(member);
    setShowForm(true);
  };

  const deleteMember = async (memberId) => {
    if (window.confirm('Sei sicuro di voler eliminare questo membro?')) {
      try {
        await apiService.deleteMember(memberId);
        loadMembers();
      } catch (error) {
        console.error('Error deleting member:', error);
        alert('Errore nell\'eliminare il membro: ' + error.message);
      }
    }
  };

  if (loading) {
    return <div className="loading">Caricamento membri...</div>;
  }

  return (
    <div className="members">
      <div className="container">
        <div className="page-header">
          <h2>Gestione Membri</h2>
          <button 
            className="btn btn-primary"
            onClick={() => setShowForm(true)}
          >
            + Nuovo Membro
          </button>
        </div>

        {showForm && (
          <div className="modal-overlay">
            <div className="modal">
              <div className="modal-header">
                <h3>{editingMember ? 'Modifica Membro' : 'Nuovo Membro'}</h3>
                <button className="btn-close" onClick={resetForm}>×</button>
              </div>
              <form onSubmit={handleSubmit} className="member-form">
                <div className="form-grid">
                  <div className="form-group">
                    <label>Nome</label>
                    <input
                      type="text"
                      value={formData.firstName}
                      onChange={(e) => setFormData({...formData, firstName: e.target.value})}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Cognome</label>
                    <input
                      type="text"
                      value={formData.lastName}
                      onChange={(e) => setFormData({...formData, lastName: e.target.value})}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Email</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({...formData, email: e.target.value})}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Telefono</label>
                    <input
                      type="tel"
                      value={formData.phoneNumber}
                      onChange={(e) => setFormData({...formData, phoneNumber: e.target.value})}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Tipo Abbonamento</label>
                    <select
                      value={formData.subscriptionType}
                      onChange={(e) => setFormData({...formData, subscriptionType: e.target.value})}
                    >
                      <option value="basic">Basic</option>
                      <option value="premium">Premium</option>
                      <option value="vip">VIP</option>
                    </select>
                  </div>
                </div>
                
                <div className="form-section">
                  <h4>Contatto di Emergenza</h4>
                  <div className="form-grid">
                    <div className="form-group">
                      <label>Nome</label>
                      <input
                        type="text"
                        value={formData.emergencyContact.name}
                        onChange={(e) => setFormData({
                          ...formData, 
                          emergencyContact: {...formData.emergencyContact, name: e.target.value}
                        })}
                      />
                    </div>
                    <div className="form-group">
                      <label>Telefono</label>
                      <input
                        type="tel"
                        value={formData.emergencyContact.phone}
                        onChange={(e) => setFormData({
                          ...formData, 
                          emergencyContact: {...formData.emergencyContact, phone: e.target.value}
                        })}
                      />
                    </div>
                  </div>
                </div>

                <div className="form-actions">
                  <button type="button" className="btn btn-secondary" onClick={resetForm}>
                    Annulla
                  </button>
                  <button type="submit" className="btn btn-primary">
                    {editingMember ? 'Aggiorna' : 'Crea'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        <div className="members-list">
          {members.length === 0 ? (
            <div className="empty-state">
              <p>Nessun membro trovato. Aggiungi il primo membro!</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Email</th>
                    <th>Telefono</th>
                    <th>Abbonamento</th>
                    <th>Stato</th>
                    <th>Data Iscrizione</th>
                    <th>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.memberId}>
                      <td>{member.firstName} {member.lastName}</td>
                      <td>{member.email}</td>
                      <td>{member.phoneNumber}</td>
                      <td>
                        <span className={`badge badge-${member.subscriptionType}`}>
                          {member.subscriptionType}
                        </span>
                      </td>
                      <td>
                        <span className={`status status-${member.status}`}>
                          {member.status}
                        </span>
                      </td>
                      <td>{new Date(member.joinDate).toLocaleDateString('it-IT')}</td>
                      <td>
                        <div className="actions">
                          <button 
                            className="btn btn-sm btn-secondary"
                            onClick={() => startEdit(member)}
                          >
                            Modifica
                          </button>
                          <button 
                            className="btn btn-sm btn-danger"
                            onClick={() => deleteMember(member.memberId)}
                          >
                            Elimina
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const Workouts = () => {
  const [workouts, setWorkouts] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    memberId: '',
    date: new Date().toISOString().split('T')[0],
    exercises: [{ name: '', sets: '', reps: '', weight: '' }],
    duration: '',
    caloriesBurned: '',
    notes: '',
  });

  useEffect(() => {
    loadWorkouts();
    loadMembers();
  }, []);

  const loadWorkouts = async () => {
    try {
      setLoading(true);
      const data = await apiService.getWorkouts();
      setWorkouts(data.workouts || []);
    } catch (error) {
      console.error('Error loading workouts:', error);
      // Mock data
      setWorkouts([
        {
          workoutId: '1',
          memberId: '1',
          memberName: 'Marco Rossi',
          date: '2024-08-19',
          exercises: [
            { name: 'Panca Piana', sets: '3', reps: '10', weight: '80kg' },
            { name: 'Squat', sets: '4', reps: '8', weight: '100kg' }
          ],
          duration: 60,
          caloriesBurned: 450,
          notes: 'Ottimo allenamento'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const loadMembers = async () => {
    try {
      const data = await apiService.getMembers();
      setMembers(data.members || []);
    } catch (error) {
      console.error('Error loading members:', error);
    }
  };

  const addExercise = () => {
    setFormData({
      ...formData,
      exercises: [...formData.exercises, { name: '', sets: '', reps: '', weight: '' }]
    });
  };

  const removeExercise = (index) => {
    const newExercises = formData.exercises.filter((_, i) => i !== index);
    setFormData({ ...formData, exercises: newExercises });
  };

  const updateExercise = (index, field, value) => {
    const newExercises = [...formData.exercises];
    newExercises[index][field] = value;
    setFormData({ ...formData, exercises: newExercises });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await apiService.createWorkout(formData);
      resetForm();
      loadWorkouts();
    } catch (error) {
      console.error('Error saving workout:', error);
      alert('Errore nel salvare l\'allenamento: ' + error.message);
    }
  };

  const resetForm = () => {
    setFormData({
      memberId: '',
      date: new Date().toISOString().split('T')[0],
      exercises: [{ name: '', sets: '', reps: '', weight: '' }],
      duration: '',
      caloriesBurned: '',
      notes: '',
    });
    setShowForm(false);
  };

  if (loading) {
    return <div className="loading">Caricamento allenamenti...</div>;
  }

  return (
    <div className="workouts">
      <div className="container">
        <div className="page-header">
          <h2>Gestione Allenamenti</h2>
          <button 
            className="btn btn-primary"
            onClick={() => setShowForm(true)}
          >
            + Nuovo Allenamento
          </button>
        </div>

        {showForm && (
          <div className="modal-overlay">
            <div className="modal modal-large">
              <div className="modal-header">
                <h3>Nuovo Allenamento</h3>
                <button className="btn-close" onClick={resetForm}>×</button>
              </div>
              <form onSubmit={handleSubmit} className="workout-form">
                <div className="form-grid">
                  <div className="form-group">
                    <label>Membro</label>
                    <select
                      value={formData.memberId}
                      onChange={(e) => setFormData({...formData, memberId: e.target.value})}
                      required
                    >
                      <option value="">Seleziona membro</option>
                      {members.map(member => (
                        <option key={member.memberId} value={member.memberId}>
                          {member.firstName} {member.lastName}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Data</label>
                    <input
                      type="date"
                      value={formData.date}
                      onChange={(e) => setFormData({...formData, date: e.target.value})}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Durata (minuti)</label>
                    <input
                      type="number"
                      value={formData.duration}
                      onChange={(e) => setFormData({...formData, duration: e.target.value})}
                      placeholder="60"
                    />
                  </div>
                  <div className="form-group">
                    <label>Calorie Bruciate</label>
                    <input
                      type="number"
                      value={formData.caloriesBurned}
                      onChange={(e) => setFormData({...formData, caloriesBurned: e.target.value})}
                      placeholder="450"
                    />
                  </div>
                </div>

                <div className="form-section">
                  <div className="section-header">
                    <h4>Esercizi</h4>
                    <button type="button" className="btn btn-sm btn-secondary" onClick={addExercise}>
                      + Aggiungi Esercizio
                    </button>
                  </div>
                  
                  {formData.exercises.map((exercise, index) => (
                    <div key={index} className="exercise-row">
                      <div className="exercise-grid">
                        <input
                          type="text"
                          placeholder="Nome esercizio"
                          value={exercise.name}
                          onChange={(e) => updateExercise(index, 'name', e.target.value)}
                        />
                        <input
                          type="text"
                          placeholder="Serie"
                          value={exercise.sets}
                          onChange={(e) => updateExercise(index, 'sets', e.target.value)}
                        />
                        <input
                          type="text"
                          placeholder="Ripetizioni"
                          value={exercise.reps}
                          onChange={(e) => updateExercise(index, 'reps', e.target.value)}
                        />
                        <input
                          type="text"
                          placeholder="Peso"
                          value={exercise.weight}
                          onChange={(e) => updateExercise(index, 'weight', e.target.value)}
                        />
                        {formData.exercises.length > 1 && (
                          <button 
                            type="button" 
                            className="btn btn-sm btn-danger"
                            onClick={() => removeExercise(index)}
                          >
                            Rimuovi
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="form-group">
                  <label>Note</label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({...formData, notes: e.target.value})}
                    placeholder="Note sull'allenamento..."
                    rows="3"
                  />
                </div>

                <div className="form-actions">
                  <button type="button" className="btn btn-secondary" onClick={resetForm}>
                    Annulla
                  </button>
                  <button type="submit" className="btn btn-primary">
                    Salva Allenamento
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        <div className="workouts-list">
          {workouts.length === 0 ? (
            <div className="empty-state">
              <p>Nessun allenamento registrato. Aggiungi il primo!</p>
            </div>
          ) : (
            <div className="workouts-grid">
              {workouts.map((workout) => (
                <div key={workout.workoutId} className="workout-card">
                  <div className="workout-header">
                    <h3>{workout.memberName}</h3>
                    <span className="workout-date">
                      {new Date(workout.date).toLocaleDateString('it-IT')}
                    </span>
                  </div>
                  <div className="workout-stats">
                    <div className="stat">
                      <span className="stat-label">Durata</span>
                      <span className="stat-value">{workout.duration} min</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Calorie</span>
                      <span className="stat-value">{workout.caloriesBurned}</span>
                    </div>
                  </div>
                  <div className="workout-exercises">
                    <h4>Esercizi</h4>
                    {workout.exercises.map((exercise, index) => (
                      <div key={index} className="exercise-item">
                        <span className="exercise-name">{exercise.name}</span>
                        <span className="exercise-details">
                          {exercise.sets}x{exercise.reps} - {exercise.weight}
                        </span>
                      </div>
                    ))}
                  </div>
                  {workout.notes && (
                    <div className="workout-notes">
                      <p>{workout.notes}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const Subscriptions = () => (
  <div className="subscriptions">
    <div className="container">
      <h2>Gestione Abbonamenti</h2>
      <p>Sezione in sviluppo - Gestione abbonamenti e pagamenti</p>
    </div>
  </div>
);

const Equipment = () => (
  <div className="equipment">
    <div className="container">
      <h2>Gestione Attrezzature</h2>
      <p>Sezione in sviluppo - Inventario e manutenzione attrezzature</p>
    </div>
  </div>
);

// Main App Component
function App() {
  return (
    <Router>
      <div className="App">
        <Header />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/members" element={<Members />} />
            <Route path="/workouts" element={<Workouts />} />
            <Route path="/subscriptions" element={<Subscriptions />} />
            <Route path="/equipment" element={<Equipment />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;