import React from 'react';
import { View, StyleSheet, ScrollView, Text } from 'react-native';
import { Card, Title, Chip, List } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';

const FinancesScreen: React.FC = () => {
  const balance = {
    total: 125000,
    paid: 75000,
    pending: 50000,
  };

  const transactions = [
    { id: '1', description: 'Tuition Fee - Semester 1', amount: -75000, date: '2024-08-15' },
    { id: '2', description: 'Library Fine', amount: -500, date: '2024-09-10' },
    { id: '3', description: 'Scholarship Credit', amount: 25000, date: '2024-08-01' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Title style={styles.title}>Financial Overview</Title>

        <Card style={styles.balanceCard}>
          <Card.Content>
            <Text style={styles.balanceLabel}>Total Fees</Text>
            <Text style={styles.balanceAmount}>₹{balance.total.toLocaleString()}</Text>
            <View style={styles.balanceDetails}>
              <View style={styles.balanceItem}>
                <Text style={styles.detailLabel}>Paid</Text>
                <Text style={styles.paidAmount}>₹{balance.paid.toLocaleString()}</Text>
              </View>
              <View style={styles.balanceItem}>
                <Text style={styles.detailLabel}>Pending</Text>
                <Text style={styles.pendingAmount}>₹{balance.pending.toLocaleString()}</Text>
              </View>
            </View>
          </Card.Content>
        </Card>

        <Card style={styles.transactionsCard}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Recent Transactions</Title>
            <List.Section>
              {transactions.map((transaction) => (
                <List.Item
                  key={transaction.id}
                  title={transaction.description}
                  description={transaction.date}
                  right={() => (
                    <Text style={transaction.amount < 0 ? styles.debit : styles.credit}>
                      {transaction.amount < 0 ? '-' : '+'}₹{Math.abs(transaction.amount).toLocaleString()}
                    </Text>
                  )}
                />
              ))}
            </List.Section>
          </Card.Content>
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  balanceCard: {
    marginBottom: 16,
    elevation: 2,
  },
  balanceLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  balanceAmount: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#1a365d',
    marginBottom: 16,
  },
  balanceDetails: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    paddingTop: 16,
  },
  balanceItem: {
    alignItems: 'center',
  },
  detailLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  paidAmount: {
    fontSize: 18,
    fontWeight: '600',
    color: '#4CAF50',
  },
  pendingAmount: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FF9800',
  },
  transactionsCard: {
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  debit: {
    color: '#f44336',
    fontWeight: '500',
  },
  credit: {
    color: '#4CAF50',
    fontWeight: '500',
  },
});

export default FinancesScreen;