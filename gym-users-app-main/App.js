import React, { useState, useEffect } from 'react';
import { Users, Plus, Calendar, Phone, Mail, MapPin, Heart, AlertCircle, Activity } from 'lucide-react';

const GymUsersApp = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);

  // URL della tua API
  const API_BASE_URL = https://nahj9gcdg0.execute-api.us-east-1.amazonaws.com/nuovafase

  // Fetch tutti gli utenti
  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/users`);
      if (!response.ok) throw new Error('Failed to fetch users');
      const data = await response.json();
      setUsers(data);
    } catch (err) {
      setError('Errore nel caricamento utenti: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Crea nuovo utente casuale
  const createRandomUser = async () => {
    setCreating(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      if (!response.ok) throw new Error('Failed to create user');
      const data = await response.json();
      
      // Aggiorna la lista
      await fetchUsers();
      
    } catch (err) {
      setError('Errore nella creazione utente: ' + err.message);
    } finally {
      setCreating(false);
    }
  };

  // Carica utenti all'avvio
  useEffect(() => {
    fetchUsers();
  }, []);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('it-IT');
  };

  const getMembershipColor = (type) => {
    const colors = {
      basic: 'bg-gray-100 text-gray-800',
      monthly: 'bg-blue-100 text-blue-800',
      annual: 'bg-green-100 text-green-800',
      premium: 'bg-purple-100 text-purple-800',
      student: 'bg-yellow-100 text-yellow-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-lg border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="bg-indigo-600 p-2 rounded-lg">
                <Users className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">FitTracker</h1>
                <p className="text-gray-600">Sistema di gestione utenti palestra</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm text-gray-500">Utenti totali</p>
                <p className="text-2xl font-bold text-indigo-600">{users.length}</p>
              </div>
              <button
                onClick={createRandomUser}
                disabled={creating}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white px-6 py-3 rounded-lg font-semibold flex items-center space-x-2 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-1"
              >
                <Plus className="h-5 w-5" />
                <span>{creating ? 'Creando...' : 'Nuovo Utente'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center space-x-3">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Controls */}
        <div className="mb-6 flex justify-between items-center">
          <button
            onClick={fetchUsers}
            disabled={loading}
            className="bg-white hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg border border-gray-300 flex items-center space-x-2 transition-colors"
          >
            <Activity className="h-4 w-4" />
            <span>{loading ? 'Caricando...' : 'Aggiorna Lista'}</span>
          </button>
        </div>

        {/* Users Grid */}
        {loading && users.length === 0 ? (
          <div className="flex justify-center items-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Caricamento utenti...</p>
            </div>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {users.map((user) => (
              <div key={user.userId} className="bg-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-2 overflow-hidden border border-gray-100">
                
                {/* Card Header */}
                <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-4 text-white">
                  <div className="flex items-center space-x-3">
                    <div className="bg-white bg-opacity-20 p-2 rounded-full">
                      <Users className="h-6 w-6" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold">{user.firstName} {user.lastName}</h3>
                      <p className="text-indigo-100">Membro dal {formatDate(user.membershipStartDate)}</p>
                    </div>
                  </div>
                </div>

                {/* Card Content */}
                <div className="p-4 space-y-4">
                  
                  {/* Membership Info */}
                  <div className="flex justify-between items-center">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getMembershipColor(user.membershipType)}`}>
                      {user.membershipType.toUpperCase()}
                    </span>
                    <span className={`px-2 py-1 rounded-full text-xs ${user.isActive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {user.isActive ? 'Attivo' : 'Inattivo'}
                    </span>
                  </div>

                  {/* Goal */}
                  <div className="bg-orange-50 p-3 rounded-lg border border-orange-200">
                    <p className="text-sm font-medium text-orange-800 flex items-center space-x-2">
                      <Activity className="h-4 w-4" />
                      <span>Obiettivo: {user.goal}</span>
                    </p>
                  </div>

                  {/* Contact Info */}
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2 text-gray-600">
                      <Mail className="h-4 w-4" />
                      <span className="text-sm truncate">{user.email}</span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-600">
                      <Phone className="h-4 w-4" />
                      <span className="text-sm">{user.phone}</span>
                    </div>
                    <div className="flex items-center space-x-2 text-gray-600">
                      <MapPin className="h-4 w-4" />
                      <span className="text-sm">{user.address.street}, {user.address.city}</span>
                    </div>
                  </div>

                  {/* Birth Date */}
                  <div className="flex items-center space-x-2 text-gray-600">
                    <Calendar className="h-4 w-4" />
                    <span className="text-sm">Nato il {formatDate(user.birthDate)}</span>
                  </div>

                  {/* Emergency Contact */}
                  <div className="bg-red-50 p-3 rounded-lg border border-red-200">
                    <div className="flex items-center space-x-2 mb-1">
                      <Heart className="h-4 w-4 text-red-600" />
                      <span className="text-sm font-medium text-red-800">Contatto Emergenza</span>
                    </div>
                    <p className="text-sm text-red-700">{user.emergencyContact.name}</p>
                    <p className="text-sm text-red-600">{user.emergencyContact.phone}</p>
                    <p className="text-xs text-red-500">{user.emergencyContact.relationship}</p>
                  </div>

                  {/* Medical Info */}
                  {(user.medicalInfo.allergies !== 'Nessuna' || user.medicalInfo.conditions !== 'Nessuna') && (
                    <div className="bg-yellow-50 p-3 rounded-lg border border-yellow-200">
                      <div className="flex items-center space-x-2 mb-1">
                        <AlertCircle className="h-4 w-4 text-yellow-600" />
                        <span className="text-sm font-medium text-yellow-800">Info Mediche</span>
                      </div>
                      {user.medicalInfo.allergies !== 'Nessuna' && (
                        <p className="text-sm text-yellow-700">Allergie: {user.medicalInfo.allergies}</p>
                      )}
                      {user.medicalInfo.conditions !== 'Nessuna' && (
                        <p className="text-sm text-yellow-700">Condizioni: {user.medicalInfo.conditions}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && users.length === 0 && !error && (
          <div className="text-center py-12">
            <Users className="h-24 w-24 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">Nessun utente trovato</h3>
            <p className="text-gray-600 mb-6">Inizia creando il primo utente della palestra!</p>
            <button
              onClick={createRandomUser}
              disabled={creating}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-lg font-semibold flex items-center space-x-2 mx-auto"
            >
              <Plus className="h-5 w-5" />
              <span>Crea Primo Utente</span>
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-gray-600">
            <p>FitTracker - Sistema di gestione palestra</p>
            <p className="text-sm">Powered by AWS Lambda + DynamoDB</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default GymUsersApp;
