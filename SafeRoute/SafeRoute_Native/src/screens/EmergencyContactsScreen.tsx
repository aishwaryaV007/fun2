import React, { useState, useEffect } from 'react';
import {
    StyleSheet,
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    TextInput,
    Alert,
    FlatList,
    ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import logger from '../utils/logger';

interface EmergencyContact {
    id: string;
    name: string;
    phone: string;
    relation: string;
    isPrimary: boolean;
}

const EMERGENCY_CONTACTS_KEY = '@emergency_contacts';

export const EmergencyContactsScreen: React.FC = () => {
    const navigation = useNavigation();
    const [contacts, setContacts] = useState<EmergencyContact[]>([]);
    const [loading, setLoading] = useState(true);
    const [showAddForm, setShowAddForm] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        phone: '',
        relation: '',
    });

    useEffect(() => {
        loadContacts();
    }, []);

    const loadContacts = async () => {
        try {
            const stored = await AsyncStorage.getItem(EMERGENCY_CONTACTS_KEY);
            if (stored) {
                setContacts(JSON.parse(stored));
            }
            logger.info('[EmergencyContacts] Contacts loaded');
        } catch (error) {
            logger.error('[EmergencyContacts] Failed to load contacts:', error);
            Alert.alert('Error', 'Failed to load contacts');
        } finally {
            setLoading(false);
        }
    };

    const saveContacts = async (newContacts: EmergencyContact[]) => {
        try {
            await AsyncStorage.setItem(EMERGENCY_CONTACTS_KEY, JSON.stringify(newContacts));
            setContacts(newContacts);
            logger.info('[EmergencyContacts] Contacts saved');
        } catch (error) {
            logger.error('[EmergencyContacts] Failed to save contacts:', error);
            Alert.alert('Error', 'Failed to save contacts');
        }
    };

    const validateForm = (): boolean => {
        if (!formData.name.trim()) {
            Alert.alert('Validation Error', 'Please enter contact name');
            return false;
        }
        if (!formData.phone.trim()) {
            Alert.alert('Validation Error', 'Please enter phone number');
            return false;
        }
        if (!/^\d{10}$/.test(formData.phone.replace(/\D/g, ''))) {
            Alert.alert('Validation Error', 'Please enter a valid 10-digit phone number');
            return false;
        }
        return true;
    };

    const addContact = () => {
        if (!validateForm()) return;

        const newContact: EmergencyContact = {
            id: Date.now().toString(),
            name: formData.name.trim(),
            phone: formData.phone.trim(),
            relation: formData.relation.trim() || 'Emergency Contact',
            isPrimary: contacts.length === 0, // First contact is primary
        };

        const newContacts = [...contacts, newContact];
        saveContacts(newContacts);
        setFormData({ name: '', phone: '', relation: '' });
        setShowAddForm(false);
        logger.info('[EmergencyContacts] Contact added:', { name: newContact.name });
    };

    const deleteContact = (id: string) => {
        Alert.alert(
            'Delete Contact',
            'Are you sure you want to delete this contact?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Delete',
                    style: 'destructive',
                    onPress: () => {
                        const newContacts = contacts.filter((c) => c.id !== id);
                        // If deleted contact was primary, make first remaining contact primary
                        if (newContacts.length > 0 && !newContacts.some((c) => c.isPrimary)) {
                            newContacts[0].isPrimary = true;
                        }
                        saveContacts(newContacts);
                        logger.info('[EmergencyContacts] Contact deleted');
                    },
                },
            ]
        );
    };

    const togglePrimary = (id: string) => {
        const newContacts = contacts.map((c) => ({
            ...c,
            isPrimary: c.id === id,
        }));
        saveContacts(newContacts);
        logger.info('[EmergencyContacts] Primary contact changed');
    };

    const renderContactItem = ({ item }: { item: EmergencyContact }) => (
        <View style={styles.contactCard}>
            <View style={styles.contactInfo}>
                <View style={styles.contactHeader}>
                    <Text style={styles.contactName}>{item.name}</Text>
                    {item.isPrimary && (
                        <View style={styles.primaryBadge}>
                            <Text style={styles.primaryText}>Primary</Text>
                        </View>
                    )}
                </View>
                <Text style={styles.contactRelation}>{item.relation}</Text>
                <Text style={styles.contactPhone}>{item.phone}</Text>
            </View>

            <View style={styles.contactActions}>
                <TouchableOpacity
                    style={[styles.actionButton, !item.isPrimary && styles.primaryButton]}
                    onPress={() => togglePrimary(item.id)}
                >
                    <Text style={styles.actionButtonText}>
                        {item.isPrimary ? '★' : '☆'}
                    </Text>
                </TouchableOpacity>
                <TouchableOpacity
                    style={[styles.actionButton, styles.deleteButton]}
                    onPress={() => deleteContact(item.id)}
                >
                    <Text style={styles.actionButtonText}>🗑️</Text>
                </TouchableOpacity>
            </View>
        </View>
    );

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color="#4CAF50" />
            </View>
        );
    }

    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity
                    style={styles.backButton}
                    onPress={() => navigation.goBack()}
                >
                    <Text style={styles.backButtonText}>← Back</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Emergency Contacts</Text>
                <View style={styles.headerSpacer} />
            </View>

            {/* Info */}
            <View style={styles.infoBox}>
                <Text style={styles.infoText}>
                    Add emergency contacts who will be notified during SOS alerts.
                </Text>
            </View>

            {/* Contacts List */}
            {contacts.length > 0 ? (
                <FlatList
                    data={contacts}
                    renderItem={renderContactItem}
                    keyExtractor={(item) => item.id}
                    contentContainerStyle={styles.listContainer}
                    scrollEnabled={false}
                />
            ) : (
                <View style={styles.emptyState}>
                    <Text style={styles.emptyText}>No emergency contacts yet</Text>
                    <Text style={styles.emptySubtext}>Add your first contact below</Text>
                </View>
            )}

            {/* Add Contact Form */}
            {showAddForm ? (
                <ScrollView style={styles.formContainer}>
                    <Text style={styles.formTitle}>Add Emergency Contact</Text>

                    <View style={styles.formGroup}>
                        <Text style={styles.label}>Name *</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="Full name"
                            value={formData.name}
                            onChangeText={(text) => setFormData({ ...formData, name: text })}
                            placeholderTextColor="#bbb"
                        />
                    </View>

                    <View style={styles.formGroup}>
                        <Text style={styles.label}>Phone *</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="10-digit phone number"
                            value={formData.phone}
                            onChangeText={(text) =>
                                setFormData({ ...formData, phone: text.replace(/\D/g, '') })
                            }
                            keyboardType="phone-pad"
                            maxLength={10}
                            placeholderTextColor="#bbb"
                        />
                    </View>

                    <View style={styles.formGroup}>
                        <Text style={styles.label}>Relation</Text>
                        <TextInput
                            style={styles.input}
                            placeholder="e.g., Sister, Friend, Parent"
                            value={formData.relation}
                            onChangeText={(text) => setFormData({ ...formData, relation: text })}
                            placeholderTextColor="#bbb"
                        />
                    </View>

                    <TouchableOpacity style={styles.submitButton} onPress={addContact}>
                        <Text style={styles.submitButtonText}>Add Contact</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={styles.cancelButton}
                        onPress={() => {
                            setShowAddForm(false);
                            setFormData({ name: '', phone: '', relation: '' });
                        }}
                    >
                        <Text style={styles.cancelButtonText}>Cancel</Text>
                    </TouchableOpacity>
                </ScrollView>
            ) : (
                <TouchableOpacity
                    style={styles.addButton}
                    onPress={() => setShowAddForm(true)}
                >
                    <Text style={styles.addButtonText}>+ Add Emergency Contact</Text>
                </TouchableOpacity>
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#f5f5f5',
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 20,
        paddingTop: 50,
        paddingBottom: 20,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#e0e0e0',
    },
    backButton: {
        padding: 8,
    },
    backButtonText: {
        fontSize: 16,
        color: '#4CAF50',
        fontWeight: '600',
    },
    headerTitle: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#333',
    },
    headerSpacer: {
        width: 60,
    },
    infoBox: {
        backgroundColor: '#e8f5e9',
        margin: 20,
        padding: 12,
        borderRadius: 8,
        borderLeftWidth: 4,
        borderLeftColor: '#4CAF50',
    },
    infoText: {
        fontSize: 13,
        color: '#2e7d32',
        lineHeight: 18,
    },
    listContainer: {
        paddingHorizontal: 20,
        paddingBottom: 20,
    },
    emptyState: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 40,
    },
    emptyText: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#999',
        marginBottom: 8,
    },
    emptySubtext: {
        fontSize: 14,
        color: '#bbb',
        textAlign: 'center',
    },
    contactCard: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    contactInfo: {
        flex: 1,
    },
    contactHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 4,
    },
    contactName: {
        fontSize: 16,
        fontWeight: '600',
        color: '#333',
        marginRight: 8,
    },
    primaryBadge: {
        backgroundColor: '#4CAF50',
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 4,
    },
    primaryText: {
        fontSize: 10,
        color: '#fff',
        fontWeight: 'bold',
    },
    contactRelation: {
        fontSize: 12,
        color: '#999',
        marginBottom: 2,
    },
    contactPhone: {
        fontSize: 14,
        color: '#666',
        fontWeight: '500',
    },
    contactActions: {
        flexDirection: 'row',
        gap: 8,
    },
    actionButton: {
        width: 40,
        height: 40,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
    },
    primaryButton: {
        backgroundColor: '#ffe0b2',
    },
    deleteButton: {
        backgroundColor: '#ffebee',
    },
    actionButtonText: {
        fontSize: 18,
    },
    formContainer: {
        backgroundColor: '#fff',
        padding: 20,
        borderTopWidth: 1,
        borderTopColor: '#e0e0e0',
        maxHeight: 400,
    },
    formTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#333',
        marginBottom: 20,
    },
    formGroup: {
        marginBottom: 16,
    },
    label: {
        fontSize: 14,
        fontWeight: '600',
        color: '#333',
        marginBottom: 8,
    },
    input: {
        borderWidth: 1,
        borderColor: '#ddd',
        borderRadius: 8,
        padding: 12,
        fontSize: 14,
        color: '#333',
        backgroundColor: '#f9f9f9',
    },
    submitButton: {
        backgroundColor: '#4CAF50',
        borderRadius: 8,
        padding: 14,
        alignItems: 'center',
        marginBottom: 12,
    },
    submitButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
    cancelButton: {
        backgroundColor: '#f5f5f5',
        borderRadius: 8,
        padding: 14,
        alignItems: 'center',
    },
    cancelButtonText: {
        color: '#666',
        fontSize: 16,
        fontWeight: '600',
    },
    addButton: {
        backgroundColor: '#4CAF50',
        margin: 20,
        marginTop: 'auto',
        borderRadius: 8,
        padding: 16,
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 5,
        elevation: 8,
    },
    addButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
});